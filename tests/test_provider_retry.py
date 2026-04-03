import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from xservice.providers.base import BaseProvider
from xservice.providers.exceptions import OperationError, SessionAcquisitionError
from xservice.providers.models import Session
from xservice.providers.session_pool import SessionPool


@pytest.fixture
def session_pool():
    """Fixture for an empty SessionPool."""
    return SessionPool()


@pytest.fixture
def provider(session_pool: SessionPool) -> BaseProvider:
    """Fixture for a BaseProvider using the session_pool."""
    return BaseProvider(session_pool)


@pytest.fixture
def session_a() -> Session:
    """Fixture for a sample session 'a'."""
    return Session(session_id="a", headers={"Auth": "a"}, cookies={"c": "a"})


@pytest.fixture
def session_b() -> Session:
    """Fixture for a sample session 'b'."""
    return Session(session_id="b", headers={"Auth": "b"}, cookies={"c": "b"})


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_retry_on_403_then_success(
    mock_request: AsyncMock,
    provider: BaseProvider,
    session_pool: SessionPool,
    session_a: Session,
    session_b: Session,
):
    """
    Tests that a 403 error with one session causes a retry that succeeds
    with another session.
    """
    op = "test_op"
    # Session B has higher quota, so it will be picked first.
    session_a.rate_limit_info = {op: {"remaining": 10}}
    session_b.rate_limit_info = {op: {"remaining": 50}}
    await session_pool.add_session(session_a)
    await session_pool.add_session(session_b)

    # Mock the upstream responses.
    # The first call (with session B) will get a 403.
    # The second call (with session A) will succeed.
    mock_request.side_effect = [
        httpx.Response(
            403,
            request=httpx.Request("GET", "http://test"),
            text="Forbidden",
        ),
        httpx.Response(
            200,
            request=httpx.Request("GET", "http://test"),
            json={"data": "success"},
        ),
    ]

    result = await provider._request("GET", "http://test", operation=op)

    assert result == {"data": "success"}
    assert mock_request.call_count == 2

    # Verify the first call was with session B (highest quota)
    first_call_headers = mock_request.call_args_list[0].kwargs["headers"]
    assert first_call_headers["Auth"] == "b"

    # Verify the second call was with session A
    second_call_headers = mock_request.call_args_list[1].kwargs["headers"]
    assert second_call_headers["Auth"] == "a"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_all_sessions_fail_403(
    mock_request: AsyncMock,
    provider: BaseProvider,
    session_pool: SessionPool,
    session_a: Session,
    session_b: Session,
):
    """
    Tests that if all available sessions return a 403 error, the
    OperationError from the last attempt is raised.
    """
    op = "test_op"
    await session_pool.add_session(session_a)
    await session_pool.add_session(session_b)

    # Mock all upstream responses to be 403 Forbidden.
    mock_request.return_value = httpx.Response(
        403,
        request=httpx.Request("GET", "http://test"),
        text="Forbidden",
    )

    with pytest.raises(OperationError) as exc_info:
        await provider._request("GET", "http://test", operation=op)

    assert "Upstream auth error: 403" in str(exc_info.value)
    assert mock_request.call_count == 2


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_no_retry_on_non_40x_error(
    mock_request: AsyncMock,
    provider: BaseProvider,
    session_pool: SessionPool,
    session_a: Session,
):
    """
    Tests that a non-401/403 HTTP error does not trigger a retry.
    """
    await session_pool.add_session(session_a)

    mock_request.return_value = httpx.Response(
        500,
        request=httpx.Request("GET", "http://test"),
        text="Internal Server Error",
    )

    with pytest.raises(OperationError) as exc_info:
        await provider._request("GET", "http://test", operation="test_op")

    assert "HTTP error: 500" in str(exc_info.value)
    assert mock_request.call_count == 1


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_highest_quota_selection_is_preserved(
    mock_request: AsyncMock,
    provider: BaseProvider,
    session_pool: SessionPool,
    session_a: Session,
    session_b: Session,
):
    """
    Tests that the session with the highest quota is still chosen first.
    """
    op = "test_op"
    session_a.rate_limit_info = {op: {"remaining": 10}}
    session_b.rate_limit_info = {op: {"remaining": 50}}
    await session_pool.add_session(session_a)
    await session_pool.add_session(session_b)

    mock_request.return_value = httpx.Response(
        200,
        request=httpx.Request("GET", "http://test"),
        json={"data": "success"},
    )

    await provider._request("GET", "http://test", operation=op)

    assert mock_request.call_count == 1
    # The call should have been made with session B's headers.
    first_call_headers = mock_request.call_args_list[0].kwargs["headers"]
    assert first_call_headers["Auth"] == "b"

@pytest.mark.asyncio
async def test_no_sessions_available(provider: BaseProvider, session_pool: SessionPool):
    """
    Tests that SessionAcquisitionError is raised if the pool is empty and closed.
    """
    await session_pool.close()
    with pytest.raises(SessionAcquisitionError):
        await provider._request("GET", "http://test", operation="test_op")

@pytest.mark.asyncio
@patch("httpx.AsyncClient.request", new_callable=AsyncMock)
async def test_session_released_on_success(
    mock_request: AsyncMock,
    provider: BaseProvider,
    session_pool: SessionPool,
    session_a: Session,
):
    """
    Tests that a session is correctly released after a successful request.
    """
    await session_pool.add_session(session_a)
    assert session_pool.available_size == 1

    mock_request.return_value = httpx.Response(
        200,
        request=httpx.Request("GET", "http://test"),
        json={"data": "success"},
    )

    await provider._request("GET", "http://test", operation="test_op")

    # The session should have been acquired, making the pool empty, then released.
    assert session_pool.available_size == 1
    # Check if we can get it again
    session = await session_pool.get_session()
    assert session is not None
    assert session.session_id == "a"

