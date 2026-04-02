import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """
    Base model for all database models.
    """

    type_annotation_map = {dict[str, str]: JSON}


class TimestampedModel(Base):
    """
    Abstract base model with created_at and updated_at timestamps.
    """

    __abstract__ = True

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class ApiKey(TimestampedModel):
    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    # A comment to help identify the key, e.g. "CI key"
    comment: Mapped[str] = mapped_column(String, nullable=False)

    def __repr__(self) -> str:
        return f"<ApiKey id={self.id} comment='{self.comment}'>"


class XAccountSession(TimestampedModel):
    """
    Represents a session for a single X account.
    """

    __tablename__ = "x_account_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    # A unique session ID for this account
    session_id: Mapped[uuid.UUID] = mapped_column(
        "session_id", unique=True, default=uuid.uuid4
    )
    # The X account username, e.g. "@elonmusk"
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    # A label for the session, e.g. "Main account"
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Provider-specific state, stored as JSON
    cookies: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    headers: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)
    rate_limit_state: Mapped[dict[str, str] | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<XAccountSession id={self.id} username='{self.username}'>"
