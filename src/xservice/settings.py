from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "xservice"
    API_V1_STR: str = "/api/v1"

    # For local development, a SQLite database is used by default.
    # You can override this with a PostgreSQL connection string.
    # e.g., DATABASE_URL=postgresql://user:password@localhost/xservice
    DATABASE_URL: str = "sqlite:///./xservice-dev.db"


settings = Settings()
