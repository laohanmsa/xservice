import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable
from typing import Dict, Optional

from .models import Session


class SessionPool:
    """A simple in-memory session pool."""

    def __init__(
        self,
        on_rate_limit_update: Callable[[int, dict[str, dict[str, int]]], Awaitable[None] | None]
        | None = None,
    ) -> None:
        self._sessions: Dict[str, Session] = {}
        self._available_sessions: asyncio.Queue[str] = asyncio.Queue()
        self._lock = asyncio.Lock()
        self._closed = False
        self._on_rate_limit_update = on_rate_limit_update

    async def add_session(self, session: Session) -> None:
        """Add a session to the pool."""
        async with self._lock:
            if self._closed:
                raise RuntimeError("SessionPool is closed.")
            if session.session_id not in self._sessions:
                self._sessions[session.session_id] = session
                await self._available_sessions.put(session.session_id)

    async def get_session(self) -> Optional[Session]:
        """Get an available session from the pool.

        Waits for a session to become available if none are currently free.
        """
        if self._closed:
            return None

        session_id = await self._available_sessions.get()
        async with self._lock:
            if self._closed:
                # This can happen if close() is called while a task is waiting on the queue
                await self._available_sessions.put(session_id)  # Put it back
                return None

            session = self._sessions.get(session_id)
            if session:
                session.in_use = True
                session.last_used = time.time()
                return session
        return None  # Should not happen in normal operation

    async def release_session(self, session_id: str) -> None:
        """Release a session back to the pool."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if session:
                session.in_use = False
                if not self._closed:
                    await self._available_sessions.put(session_id)

    async def update_rate_limit(
        self, session_id: str, operation: str, rate_limit_state: dict[str, int]
    ) -> None:
        session = self._sessions.get(session_id)
        if not session:
            return

        if not isinstance(session.rate_limit_info, dict):
            session.rate_limit_info = {}
        elif "limit" in session.rate_limit_info and "remaining" in session.rate_limit_info:
            session.rate_limit_info = {"default": session.rate_limit_info}

        session.rate_limit_info[operation] = rate_limit_state
        if self._on_rate_limit_update and session.db_id is not None:
            result = self._on_rate_limit_update(session.db_id, session.rate_limit_info)
            if inspect.isawaitable(result):
                await result

    @property
    def size(self) -> int:
        """Return the total number of sessions in the pool."""
        return len(self._sessions)

    @property
    def available_size(self) -> int:
        """Return the number of available sessions."""
        return self._available_sessions.qsize()

    async def close(self) -> None:
        """Close the session pool and prevent further use."""
        async with self._lock:
            if self._closed:
                return
            self._closed = True
            # Empty the queue
            while not self._available_sessions.empty():
                try:
                    self._available_sessions.get_nowait()
                except asyncio.QueueEmpty:
                    break
            self._sessions.clear()
