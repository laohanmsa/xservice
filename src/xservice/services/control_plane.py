import json
import secrets
import uuid
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from .. import models, schemas
from ..logging import log

_X_BEARER_TOKEN = (
    "Bearer "
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs="
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
)


def _normalize_rate_limit_state(
    rate_limit_state: Any | None,
) -> dict[str, Any]:
    if not rate_limit_state:
        return {}

    if isinstance(rate_limit_state, str):
        try:
            rate_limit_state = json.loads(rate_limit_state)
        except json.JSONDecodeError:
            log.warning("Failed to parse rate_limit_state: %s", rate_limit_state)
            return {}

    if not isinstance(rate_limit_state, dict):
        return {}

    if "limit" in rate_limit_state and "remaining" in rate_limit_state:
        return {"default": rate_limit_state}
    return rate_limit_state



def _parse_cookie_string(cookie_string: str) -> dict[str, str]:
    parsed = SimpleCookie()
    parsed.load(cookie_string)
    return {key: morsel.value for key, morsel in parsed.items()}


def _derive_session_username(username: str | None, cookies: dict[str, str]) -> str:
    if username:
        return username

    twid = cookies.get("twid", "").strip('"')
    if twid.startswith("u="):
        return f"user_{twid.removeprefix('u=')}"
    if twid.startswith("u%3D"):
        return f"user_{twid.removeprefix('u%3D')}"
    return f"session-{secrets.token_hex(4)}"


def _build_headers_for_cookies(cookies: dict[str, str]) -> dict[str, str]:
    return {
        "authorization": _X_BEARER_TOKEN,
        "referer": "https://twitter.com/",
        "user-agent": _DEFAULT_USER_AGENT,
        "x-csrf-token": cookies.get("ct0", ""),
        "x-twitter-auth-type": "OAuth2Session" if cookies.get("auth_token") else "",
        "x-twitter-active-user": "yes",
        "x-twitter-client-language": "en",
    }


def _default_cookie_label(index: int) -> str:
    return f"default-cookie-{index}"


def _legacy_cookie_label(index: int) -> str:
    return f"legacy-cookie-{index}"


def _managed_cookie_aliases(index: int) -> set[str]:
    return {_default_cookie_label(index), _legacy_cookie_label(index)}


def _read_cookie_lines(cookie_file_path: str) -> list[str]:
    return [
        line.strip()
        for line in Path(cookie_file_path).read_text().splitlines()
        if line.strip()
    ]


class ControlPlaneService:
    def __init__(self, db: Session):
        self.db = db

    def get_api_keys(self):
        return self.db.query(models.ApiKey).all()

    def create_api_key(self, api_key: schemas.ApiKeyCreate):
        key = secrets.token_urlsafe(32)
        db_api_key = models.ApiKey(**api_key.model_dump(), key=key)
        self.db.add(db_api_key)
        self.db.commit()
        self.db.refresh(db_api_key)
        return db_api_key

    def delete_api_key(self, api_key_id: int):
        db_api_key = self.db.query(models.ApiKey).filter(models.ApiKey.id == api_key_id).first()
        if db_api_key:
            self.db.delete(db_api_key)
            self.db.commit()
        return db_api_key

    def get_sessions(self):
        return self.db.query(models.XAccountSession).all()

    def get_session_limits(self) -> list[schemas.XAccountSessionRateLimitInfo]:
        return [
            schemas.XAccountSessionRateLimitInfo(
                id=session.id,
                session_id=session.session_id,
                username=session.username,
                label=session.label,
                is_active=session.is_active,
                rate_limit_state=_normalize_rate_limit_state(session.rate_limit_state),
            )
            for session in self.get_sessions()
        ]

    def _find_session_for_default_cookie(
        self,
        sessions: list[models.XAccountSession],
        *,
        index: int,
        label: str,
        cookies: dict[str, str],
    ) -> models.XAccountSession | None:
        auth_token = cookies.get("auth_token")
        twid = cookies.get("twid")
        aliases = _managed_cookie_aliases(index)

        for session in sessions:
            if session.label in aliases or session.username in aliases:
                return session

        for session in sessions:
            existing_cookies = session.cookies or {}
            if auth_token and existing_cookies.get("auth_token") == auth_token:
                return session
            if twid and existing_cookies.get("twid") == twid:
                return session

        return None

    def bootstrap_default_sessions(
        self, *, cookie_file_path: str, expected_count: int = 4
    ) -> int:
        cookie_lines = _read_cookie_lines(cookie_file_path)
        if len(cookie_lines) < expected_count:
            log.warning(
                "startup: expected %s default cookie lines, found %s",
                expected_count,
                len(cookie_lines),
            )

        sessions = self.get_sessions()
        ensured_sessions: list[models.XAccountSession] = []

        for index, cookie_string in enumerate(cookie_lines[:expected_count], start=1):
            label = _default_cookie_label(index)
            aliases = _managed_cookie_aliases(index)
            cookies = _parse_cookie_string(cookie_string)
            headers = _build_headers_for_cookies(cookies)
            resolved_session = self._find_session_for_default_cookie(
                sessions, index=index, label=label, cookies=cookies
            )

            duplicate_alias_sessions = [
                session
                for session in list(sessions)
                if session is not resolved_session
                and (
                    (session.label or "") in aliases
                    or (session.username or "") in aliases
                )
            ]
            for session in duplicate_alias_sessions:
                if session.id is not None:
                    self.db.delete(session)
                sessions.remove(session)
            if duplicate_alias_sessions:
                self.db.flush()

            if resolved_session:
                resolved_session.username = label
                resolved_session.label = label
                resolved_session.is_active = True
                resolved_session.cookies = cookies
                resolved_session.headers = headers
                resolved_session.rate_limit_state = resolved_session.rate_limit_state or {}
            else:
                resolved_session = models.XAccountSession(
                    session_id=uuid.uuid4(),
                    username=label,
                    label=label,
                    is_active=True,
                    cookies=cookies,
                    headers=headers,
                    rate_limit_state={},
                )
                self.db.add(resolved_session)
                sessions.append(resolved_session)

            ensured_sessions.append(resolved_session)

        ensured_ids = {session.id for session in ensured_sessions if session.id is not None}
        managed_prefixes = ("default-cookie-", "legacy-cookie-")
        for session in sessions:
            if session.id is None:
                continue
            if session.id in ensured_ids:
                continue
            session_label = session.label or ""
            session_username = session.username or ""
            if session_label.startswith(managed_prefixes) or session_username.startswith(
                managed_prefixes
            ):
                self.db.delete(session)

        self.db.commit()
        for session in ensured_sessions:
            self.db.refresh(session)

        return len(ensured_sessions)

    def create_session(self, session: schemas.XAccountSessionCreate):
        db_session = models.XAccountSession(**session.model_dump(), session_id=uuid.uuid4())
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return db_session

    def create_session_from_cookie(self, session: schemas.XAccountSessionImportCookie):
        cookies = _parse_cookie_string(session.cookie_string)
        headers = _build_headers_for_cookies(cookies)
        username = _derive_session_username(session.username, cookies)

        session_create = schemas.XAccountSessionCreate(
            username=username,
            label=session.label,
            is_active=session.is_active if session.is_active is not None else True,
            cookies=cookies,
            headers=headers,
        )

        return self.create_session(session=session_create)

    def update_session(self, session_id: int, session: schemas.XAccountSessionUpdate):
        db_session = self.db.query(models.XAccountSession).filter(models.XAccountSession.id == session_id).first()
        if db_session:
            update_data = session.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(db_session, key, value)
            self.db.commit()
            self.db.refresh(db_session)
        return db_session

    def delete_session(self, session_id: int):
        db_session = self.db.query(models.XAccountSession).filter(models.XAccountSession.id == session_id).first()
        if db_session:
            self.db.delete(db_session)
            self.db.commit()
        return db_session

    def get_status(self) -> schemas.AdminStatus:
        api_key_count = self.db.query(models.ApiKey).count()
        sessions = self.get_sessions()

        session_count = len(sessions)
        active_session_count = sum(1 for s in sessions if s.is_active)
        inactive_session_count = session_count - active_session_count

        return schemas.AdminStatus(
            service_status="ok",
            api_key_count=api_key_count,
            session_count=session_count,
            active_session_count=active_session_count,
            inactive_session_count=inactive_session_count,
            sessions=[
                schemas.AdminStatusSessionSummary(
                    id=s.id,
                    session_id=s.session_id,
                    username=s.username,
                    is_active=s.is_active,
                    rate_limit_state=_normalize_rate_limit_state(s.rate_limit_state),
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
                for s in sessions
            ],
        )
