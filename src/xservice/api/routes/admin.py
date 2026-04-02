from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from xservice import schemas
from xservice.api.dependencies import get_db
from xservice.auth import get_api_key
from xservice.models import ApiKey
from xservice.services.control_plane import ControlPlaneService

router = APIRouter()


@router.get("/api-keys", response_model=List[schemas.ApiKeyMetadata])
def get_api_keys(
    db: Session = Depends(get_db), _: ApiKey = Depends(get_api_key)
):
    service = ControlPlaneService(db)
    return service.get_api_keys()


@router.post("/api-keys", response_model=schemas.ApiKey)
def create_api_key(
    api_key: schemas.ApiKeyCreate,
    db: Session = Depends(get_db),
    _: ApiKey = Depends(get_api_key),
):
    service = ControlPlaneService(db)
    return service.create_api_key(api_key=api_key)


@router.delete("/api-keys/{api_key_id}")
def delete_api_key(
    api_key_id: int, db: Session = Depends(get_db), _: ApiKey = Depends(get_api_key)
):
    service = ControlPlaneService(db)
    db_api_key = service.delete_api_key(api_key_id=api_key_id)
    if db_api_key is None:
        raise HTTPException(status_code=404, detail="API Key not found")
    return {"ok": True}


@router.get("/sessions", response_model=List[schemas.XAccountSession])
def get_sessions(
    db: Session = Depends(get_db), _: ApiKey = Depends(get_api_key)
):
    service = ControlPlaneService(db)
    return service.get_sessions()


@router.post("/sessions", response_model=schemas.XAccountSession)
def create_session(
    session: schemas.XAccountSessionCreate,
    db: Session = Depends(get_db),
    _: ApiKey = Depends(get_api_key),
):
    service = ControlPlaneService(db)
    return service.create_session(session=session)


@router.patch("/sessions/{session_id}", response_model=schemas.XAccountSession)
def update_session(
    session_id: int,
    session: schemas.XAccountSessionUpdate,
    db: Session = Depends(get_db),
    _: ApiKey = Depends(get_api_key),
):
    service = ControlPlaneService(db)
    db_session = service.update_session(session_id=session_id, session=session)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return db_session


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int, db: Session = Depends(get_db), _: ApiKey = Depends(get_api_key)
):
    service = ControlPlaneService(db)
    db_session = service.delete_session(session_id=session_id)
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"ok": True}


@router.get("/status", response_model=schemas.AdminStatus)
def get_status(
    db: Session = Depends(get_db), _: ApiKey = Depends(get_api_key)
):
    service = ControlPlaneService(db)
    return service.get_status()
