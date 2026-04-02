from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session
from starlette import status

from xservice import models
from xservice.api.dependencies import get_db

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def get_api_key(
    api_key_header: str = Security(api_key_header), db: Session = Depends(get_db)
) -> models.ApiKey:
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing API key",
        )

    api_key = db.query(models.ApiKey).filter(models.ApiKey.key == api_key_header).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key",
        )

    return api_key
