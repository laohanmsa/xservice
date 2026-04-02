import secrets
import uuid
from http.cookies import SimpleCookie

from sqlalchemy.orm import Session

from .. import models, schemas

_X_BEARER_TOKEN = (
    "Bearer "
    "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs="
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
_DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36"
)


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
            schemas.XAccountSessionRateLimitInfo.model_validate(session)
            for session in self.get_sessions()
        ]

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
                schemas.AdminStatusSessionSummary.model_validate(s) for s in sessions
            ],
        )
