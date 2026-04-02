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
