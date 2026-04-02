from typing import AsyncGenerator

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from xservice.db import get_db as get_db_session
from xservice.models import XAccountSession
from xservice.providers.models import Session as ProviderSession
from xservice.providers.session_pool import SessionPool
from xservice.providers.twitter_graphql import TwitterGraphQLProvider


def get_db() -> AsyncGenerator[Session, None]:
    """
    Returns a database session.
    """
    yield from get_db_session()


async def get_provider(
    db: Session = Depends(get_db),
) -> AsyncGenerator[TwitterGraphQLProvider, None]:
    """
    Builds a SessionPool from active DB sessions and yields a TwitterGraphQLProvider.
    """
    active_sessions = (
        db.query(XAccountSession).filter(XAccountSession.is_active == True).all()
    )
    if not active_sessions:
        raise HTTPException(
            status_code=503, detail="No active X account sessions available."
        )

    pool = SessionPool()
    for session in active_sessions:
        provider_session = ProviderSession(
            session_id=str(session.session_id),
            headers=session.headers or {},
            cookies=session.cookies or {},
            rate_limit_info=session.rate_limit_state or {},
        )
        await pool.add_session(provider_session)

    provider = TwitterGraphQLProvider(session_pool=pool)
    try:
        yield provider
    finally:
        await pool.close()
