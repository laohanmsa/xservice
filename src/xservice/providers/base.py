import logging
from typing import Any, Dict, Optional

import httpx

from .contracts import Provider
from .exceptions import OperationError, SessionAcquisitionError
from .session_pool import SessionPool

logger = logging.getLogger(__name__)


class BaseProvider(Provider):
    """Base class for providers."""

    def __init__(self, session_pool: SessionPool):
        self._session_pool = session_pool
        self._client = httpx.AsyncClient()

    async def close(self):
        """Close the provider's underlying resources."""
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        session = await self._session_pool.get_session()
        if not session:
            raise SessionAcquisitionError("No available sessions in the pool.")

        try:
            request_headers = session.headers.copy()
            if headers:
                request_headers.update(headers)

            response = await self._client.request(
                method,
                url,
                params=params,
                json=json,
                headers=request_headers,
                cookies=session.cookies,
                timeout=10.0,  # Adding a timeout for all requests
            )
            response.raise_for_status()
            rate_limit_state = _parse_rate_limit_headers(response.headers)
            if rate_limit_state:
                await self._session_pool.update_rate_limit(
                    session.session_id, rate_limit_state
                )
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                f"HTTP error occurred: {e.request.url} - {e.response.status_code}"
            )
            raise OperationError(
                f"HTTP error: {e.response.status_code}", underlying_error=e
            )
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e.request.url}")
            raise OperationError("Request error", underlying_error=e)
        finally:
            if session:
                await self._session_pool.release_session(session.session_id)


def _parse_rate_limit_headers(headers: httpx.Headers) -> dict[str, int]:
    values: dict[str, int] = {}
    for key in ("x-rate-limit-limit", "x-rate-limit-remaining", "x-rate-limit-reset"):
        raw_value = headers.get(key)
        if raw_value is None:
            return {}
        values[key.removeprefix("x-rate-limit-")] = int(raw_value)
    return values
