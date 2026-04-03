import asyncio
import pytest

from xservice.providers.models import Session
from xservice.providers.session_pool import SessionPool


@pytest.fixture
def session_pool():
    return SessionPool()


@pytest.fixture
def sample_session():
    return Session(session_id="test_session", headers={}, cookies={})


@pytest.mark.asyncio
async def test_add_and_get_session(session_pool: SessionPool, sample_session: Session):
    assert session_pool.size == 0
    await session_pool.add_session(sample_session)
    assert session_pool.size == 1
    assert session_pool.available_size == 1

    retrieved_session = await session_pool.get_session()
    assert retrieved_session is not None
    assert retrieved_session.session_id == "test_session"
    assert retrieved_session.in_use
    assert session_pool.available_size == 0


@pytest.mark.asyncio
async def test_release_session(session_pool: SessionPool, sample_session: Session):
    await session_pool.add_session(sample_session)
    session = await session_pool.get_session()
    assert session is not None
    assert session_pool.available_size == 0

    await session_pool.release_session(session.session_id)
    assert not session.in_use
    assert session_pool.available_size == 1


@pytest.mark.asyncio
async def test_get_session_waits_for_release(
    session_pool: SessionPool, sample_session: Session
):
    await session_pool.add_session(sample_session)
    session1 = await session_pool.get_session()
    assert session1 is not None

    async def get_and_check():
        session2 = await session_pool.get_session()
        assert session2 is not None
        assert session2.session_id == sample_session.session_id
        await session_pool.release_session(session2.session_id)

    task = asyncio.create_task(get_and_check())
    await asyncio.sleep(0.01)  # allow task to start and wait
    assert session_pool.available_size == 0

    await session_pool.release_session(session1.session_id)
    await task  # now this should complete


@pytest.mark.asyncio
async def test_close_pool(session_pool: SessionPool, sample_session: Session):
    await session_pool.add_session(sample_session)
    assert session_pool.size == 1

    await session_pool.close()
    assert session_pool.size == 0
    assert session_pool.available_size == 0

    # After closing, get_session should return None
    assert await session_pool.get_session() is None

    # Adding a session should raise an error
    with pytest.raises(RuntimeError):
        await session_pool.add_session(sample_session)


@pytest.mark.asyncio
async def test_concurrent_session_requests(session_pool: SessionPool):
    sessions = [
        Session(session_id=f"s{i}", headers={}, cookies={}) for i in range(5)
    ]
    for s in sessions:
        await session_pool.add_session(s)
    assert session_pool.size == 5
    assert session_pool.available_size == 5

    async def worker(worker_id):
        session = await session_pool.get_session()
        assert session is not None
        # print(f"Worker {worker_id} got session {session.session_id}")
        await asyncio.sleep(0.1)
        await session_pool.release_session(session.session_id)
        return session.session_id

    tasks = [asyncio.create_task(worker(i)) for i in range(10)]
    results = await asyncio.gather(*tasks)

    assert len(results) == 10
    assert session_pool.available_size == 5

@pytest.mark.asyncio
async def test_update_rate_limit_for_multiple_operations(
    session_pool: SessionPool, sample_session: Session
):
    """
    Proves one session retains rate-limit buckets for two different
    operations after successive updates.
    """
    await session_pool.add_session(sample_session)

    operation1 = "search"
    rate_limit1 = {"limit": 100, "remaining": 99, "reset": 1678886400}
    await session_pool.update_rate_limit(
        sample_session.session_id, operation1, rate_limit1
    )

    # force-get session to check internal state
    session = session_pool._sessions[sample_session.session_id]
    assert session.rate_limit_info == {operation1: rate_limit1}

    operation2 = "users"
    rate_limit2 = {"limit": 50, "remaining": 49, "reset": 1678886420}
    await session_pool.update_rate_limit(
        sample_session.session_id, operation2, rate_limit2
    )

    assert session.rate_limit_info == {
        operation1: rate_limit1,
        operation2: rate_limit2,
    }


@pytest.mark.asyncio
async def test_update_rate_limit_normalizes_legacy_flat_state(
    session_pool: SessionPool, sample_session: Session
):
    sample_session.rate_limit_info = {
        "limit": 187,
        "remaining": 186,
        "reset": 1775174376,
    }
    await session_pool.add_session(sample_session)

    operation = "SearchTimeline"
    current_rate_limit = {"limit": 50, "remaining": 49, "reset": 1775175000}
    await session_pool.update_rate_limit(
        sample_session.session_id, operation, current_rate_limit
    )

    session = session_pool._sessions[sample_session.session_id]
    assert session.rate_limit_info == {
        "default": {
            "limit": 187,
            "remaining": 186,
            "reset": 1775174376,
        },
        operation: current_rate_limit,
    }


@pytest.fixture
def session_b():
    return Session(session_id="test_session_b", headers={}, cookies={})


@pytest.mark.asyncio
async def test_get_session_selects_highest_quota(
    session_pool: SessionPool, sample_session: Session, session_b: Session
):
    """
    Proves get_session picks the session with the highest remaining quota
    for the requested operation.
    """
    op = "SearchTimeline"
    sample_session.rate_limit_info = {op: {"remaining": 10}}
    session_b.rate_limit_info = {op: {"remaining": 50}}
    await session_pool.add_session(sample_session)
    await session_pool.add_session(session_b)

    # First acquisition should get the one with 50 remaining
    s1 = await session_pool.get_session(operation=op)
    assert s1 is not None
    assert s1.session_id == "test_session_b"

    # Next should get the one with 10 remaining
    s2 = await session_pool.get_session(operation=op)
    assert s2 is not None
    assert s2.session_id == "test_session"

    # Release and check again
    await session_pool.release_session(s1.session_id)
    s3 = await session_pool.get_session(operation=op)
    assert s3 is not None
    assert s3.session_id == "test_session_b"


@pytest.mark.asyncio
async def test_get_session_fallback_is_queue_like(
    session_pool: SessionPool, sample_session: Session, session_b: Session
):
    """
    Proves get_session fallback (no operation or no session with op data)
    is queue-like (FIFO), not MRU/LRU.
    """
    # session_b is "less recently used", but added to the pool later.
    sample_session.last_used = 100
    session_b.last_used = 0

    # Add to pool in order: sample_session, then session_b
    await session_pool.add_session(sample_session)
    await session_pool.add_session(session_b)

    # 1. Fallback for unknown operation
    # First session out should be the first one in (sample_session)
    s1 = await session_pool.get_session(operation="unknown_op")
    assert s1 is not None
    assert s1.session_id == "test_session"

    # Second one out should be session_b
    s2 = await session_pool.get_session(operation="unknown_op")
    assert s2 is not None
    assert s2.session_id == "test_session_b"

    # Release them to make them available again
    await session_pool.release_session(s1.session_id)
    await session_pool.release_session(s2.session_id)

    # 2. Fallback for operation=None
    # First session out should be the first one that was returned to the queue
    s3 = await session_pool.get_session()
    assert s3 is not None
    assert s3.session_id == "test_session"

    s4 = await session_pool.get_session()
    assert s4 is not None
    assert s4.session_id == "test_session_b"



@pytest.mark.asyncio
async def test_get_session_ignores_legacy_flat_quota(
    session_pool: SessionPool, sample_session: Session, session_b: Session
):
    """
    Proves get_session selection logic does not break on legacy flat
    rate limit data, and correctly picks the session with modern data.
    """
    op = "SearchTimeline"
    # Legacy session
    sample_session.rate_limit_info = {"remaining": 100, "limit": 100}
    # Modern session
    session_b.rate_limit_info = {op: {"remaining": 50}}

    await session_pool.add_session(sample_session)
    await session_pool.add_session(session_b)

    session = await session_pool.get_session(operation=op)
    assert session is not None
    # It should pick the only one that has data for the operation
    assert session.session_id == "test_session_b"
