import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Health(BaseModel):
    status: str = "ok"


class ApiKeyBase(BaseModel):
    comment: str


class ApiKeyCreate(ApiKeyBase):
    pass


class ApiKey(ApiKeyBase):
    id: int
    key: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApiKeyMetadata(ApiKeyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class XAccountSessionBase(BaseModel):
    username: str
    label: str | None = None
    is_active: bool = True
    cookies: dict[str, Any] = Field(default_factory=dict)
    headers: dict[str, Any] = Field(default_factory=dict)
    rate_limit_state: dict[str, Any] = Field(default_factory=dict)


class XAccountSessionCreate(XAccountSessionBase):
    pass


class XAccountSessionUpdate(BaseModel):
    label: str | None = None
    is_active: bool | None = None
    cookies: dict[str, Any] | None = None
    headers: dict[str, Any] | None = None


class XAccountSession(XAccountSessionBase):
    id: int
    session_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminStatusSessionSummary(BaseModel):
    id: int
    session_id: uuid.UUID
    username: str
    is_active: bool
    rate_limit_state: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminStatus(BaseModel):
    service_status: str
    api_key_count: int
    session_count: int
    active_session_count: int
    inactive_session_count: int
    sessions: list[AdminStatusSessionSummary]
