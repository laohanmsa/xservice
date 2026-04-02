from fastapi import APIRouter

from xservice import schemas

router = APIRouter()


@router.get("", response_model=schemas.Health)
async def health_check() -> schemas.Health:
    return schemas.Health(status="ok")
