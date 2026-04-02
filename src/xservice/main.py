from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI

from xservice.api.routes import admin, health, search, users, tweets

from xservice.logging import log
from xservice.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("startup: commencing")
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

    @app.get("/")
    def read_root():
        return {"message": "Welcome to X-Service"}

    return app


app = create_app()
