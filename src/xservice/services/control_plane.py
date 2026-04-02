import uuid
import secrets
from sqlalchemy.orm import Session
from .. import models, schemas


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

    def create_session(self, session: schemas.XAccountSessionCreate):
        db_session = models.XAccountSession(**session.model_dump(), session_id=uuid.uuid4())
        self.db.add(db_session)
        self.db.commit()
        self.db.refresh(db_session)
        return db_session

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
