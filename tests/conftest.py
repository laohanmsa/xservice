import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from xservice.api.dependencies import get_db
from xservice.main import create_app
from xservice.models import Base, ApiKey as ApiKeyModel
from xservice.schemas import ApiKeyCreate
from xservice.settings import settings
from xservice.services.control_plane import ControlPlaneService

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def disable_default_cookie_bootstrap(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "DEFAULT_COOKIE_FILE_PATH", None)
    monkeypatch.setattr(settings, "DEFAULT_COOKIE_EXPECTED_COUNT", 4)


@pytest.fixture(name="db")
def db_fixture() -> Session:
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def client_fixture(db: Session):
    def override_get_db():
        yield db

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(db: Session) -> dict[str, str]:
    service = ControlPlaneService(db)
    api_key = service.create_api_key(api_key=ApiKeyCreate(comment="test_key"))
    return {"X-API-KEY": api_key.key}
