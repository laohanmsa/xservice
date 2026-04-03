from pathlib import Path

from sqlalchemy.orm import sessionmaker

import xservice.main as main_module
from xservice.models import XAccountSession
from xservice.schemas import XAccountSessionImportCookie
from xservice.services.control_plane import ControlPlaneService
from xservice.settings import settings


def _write_cookie_file(path: Path, count: int, *, auth_prefix: str = "auth") -> Path:
    lines = []
    for index in range(1, count + 1):
        lines.append(
            f"ct0=csrf{index}; twid=u%3D{index}; auth_token={auth_prefix}{index}=="
        )
    path.write_text("\n".join(lines))
    return path


def test_bootstrap_default_sessions_creates_expected_sessions(db, tmp_path: Path):
    cookie_file = _write_cookie_file(tmp_path / "default_cookies.txt", 4)
    service = ControlPlaneService(db)

    ensured = service.bootstrap_default_sessions(
        cookie_file_path=str(cookie_file), expected_count=4
    )

    sessions = sorted(service.get_sessions(), key=lambda session: session.label or "")
    assert ensured == 4
    assert len(sessions) == 4
    assert [session.label for session in sessions] == [
        "default-cookie-1",
        "default-cookie-2",
        "default-cookie-3",
        "default-cookie-4",
    ]
    assert all(session.is_active for session in sessions)
    assert sessions[0].cookies["auth_token"] == "auth1=="
    assert sessions[0].headers["x-csrf-token"] == "csrf1"


def test_bootstrap_default_sessions_reuses_existing_cookie_identity(db, tmp_path: Path):
    service = ControlPlaneService(db)
    legacy = service.create_session_from_cookie(
        XAccountSessionImportCookie(
            cookie_string="ct0=csrf1; twid=u%3D1; auth_token=auth1==",
            username="legacy-cookie-1",
            label="legacy-cookie-1",
        )
    )
    cookie_file = _write_cookie_file(tmp_path / "default_cookies.txt", 1)

    ensured = service.bootstrap_default_sessions(
        cookie_file_path=str(cookie_file), expected_count=1
    )

    sessions = service.get_sessions()
    assert ensured == 1
    assert len(sessions) == 1
    assert sessions[0].id == legacy.id
    assert sessions[0].username == "default-cookie-1"
    assert sessions[0].label == "default-cookie-1"
    assert sessions[0].cookies["auth_token"] == "auth1=="


def test_startup_bootstrap_uses_settings_and_session_factory(
    db, tmp_path: Path, monkeypatch
):
    cookie_file = _write_cookie_file(tmp_path / "default_cookies.txt", 2, auth_prefix="boot")
    session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=db.get_bind(),
    )

    monkeypatch.setattr(settings, "DEFAULT_COOKIE_FILE_PATH", str(cookie_file))
    monkeypatch.setattr(settings, "DEFAULT_COOKIE_EXPECTED_COUNT", 2)
    monkeypatch.setattr(main_module, "SessionLocal", session_factory)

    ensured = main_module.bootstrap_default_cookie_sessions()

    verify_db = session_factory()
    try:
        sessions = verify_db.query(XAccountSession).order_by(XAccountSession.label).all()
        assert ensured == 2
        assert [session.label for session in sessions] == [
            "default-cookie-1",
            "default-cookie-2",
        ]
    finally:
        verify_db.close()
