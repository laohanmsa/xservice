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
    ) -> Dict[str, Any]:
        session = await self._session_pool.get_session()
        if not session:
            raise SessionAcquisitionError("No available sessions in the pool.")

        try:
            response = await self._client.request(
                method,
                url,
                params=params,
                json=json,
                headers=session.headers,
                cookies=session.cookies,
                timeout=10.0,  # Adding a timeout for all requests
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e.request.url} - {e.response.status_code}")
            raise OperationError(f"HTTP error: {e.response.status_code}", underlying_error=e)
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e.request.url}")
            raise OperationError("Request error", underlying_error=e)
        finally:
            if session:
                await self._session_pool.release_session(session.session_id)
