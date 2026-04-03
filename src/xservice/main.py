from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI

from xservice.api.routes import admin, health, search, users, tweets, playground
from xservice.db import SessionLocal
from xservice.services.control_plane import ControlPlaneService

from xservice.logging import log
from xservice.settings import settings


def bootstrap_default_cookie_sessions() -> int:
    cookie_file_path = settings.DEFAULT_COOKIE_FILE_PATH
    if not cookie_file_path:
        return 0

    if not Path(cookie_file_path).exists():
        log.warning("startup: default cookie file not found at %s", cookie_file_path)
        return 0

    db = SessionLocal()
    try:
        service = ControlPlaneService(db)
        return service.bootstrap_default_sessions(
            cookie_file_path=cookie_file_path,
            expected_count=settings.DEFAULT_COOKIE_EXPECTED_COUNT,
        )
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup: commencing")
    ensured_sessions = bootstrap_default_cookie_sessions()
    if ensured_sessions:
        log.info("startup: ensured %s default cookie sessions", ensured_sessions)
    yield
    log.info("shutdown: commencing")


def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

    api_router = APIRouter()
    api_router.include_router(health.router, prefix="/health", tags=["health"])
    api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
    api_router.include_router(search.router, prefix="/search", tags=["search"])
    api_router.include_router(users.router, prefix="/users", tags=["users"])
    api_router.include_router(tweets.router, prefix="/tweets", tags=["tweets"])
    app.include_router(api_router, prefix=settings.API_V1_STR)
    app.include_router(playground.router)

    @app.get("/")
    def read_root():
        return {"message": "Welcome to X-Service"}

    return app


app = create_app()
