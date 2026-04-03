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

    async def get_session(self, operation: Optional[str] = None) -> Optional[Session]:
        """Get an available session from the pool.

        If an operation is specified, it returns the session with the highest
        remaining quota for that operation.

        Waits for a session to become available if none are currently free.
        """
        if self._closed:
            return None

        # Wait for at least one session to be available. This is the blocking part.
        initial_session_id = await self._available_sessions.get()

        async with self._lock:
            if self._closed:
                # Pool was closed after we waited.
                # Put session back and exit.
                await self._available_sessions.put(initial_session_id)
                return None

            # We now have a lock. Gather any other sessions that became available.
            other_session_ids = []
            while not self._available_sessions.empty():
                other_session_ids.append(self._available_sessions.get_nowait())

            all_ids = [initial_session_id] + other_session_ids
            available_sessions = [
                self._sessions[sid] for sid in all_ids if sid in self._sessions
            ]

            if not available_sessions:
                # This can happen if sessions were removed after their ID was queued.
                # Put the IDs back and let the caller retry.
                for sid in all_ids:
                    await self._available_sessions.put(sid)
                return None  # Caller should retry if they want.

            # Select the best session from the available ones.
            best_session = self._find_best_session(available_sessions, operation)

            # Mark the chosen session as in use.
            best_session.in_use = True
            best_session.last_used = time.time()

            # Put the other available sessions back into the queue.
            for s in available_sessions:
                if s.session_id != best_session.session_id:
                    await self._available_sessions.put(s.session_id)

            return best_session

    def _find_best_session(
        self, sessions: list[Session], operation: Optional[str]
    ) -> Session:
        """Find the best session from a list of available sessions."""
        if not sessions:
            raise ValueError("Cannot find best session in an empty list.")

        # If no operation, return first available session (queue-like)
        if not operation:
            return sessions[0]

        candidates = []
        fallback_sessions = []
        for s in sessions:
            if not isinstance(s.rate_limit_info, dict):
                fallback_sessions.append(s)
                continue

            op_quota = s.rate_limit_info.get(operation)
            if (
                isinstance(op_quota, dict)
                and "remaining" in op_quota
                and isinstance(op_quota["remaining"], int)
            ):
                candidates.append((s, op_quota["remaining"]))
            else:
                fallback_sessions.append(s)

        if candidates:
            # Sort by remaining quota, descending.
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]

        # Fallback if no session has info for this operation.
        # The list is already in a stable, dequeued order.
        return fallback_sessions[0]

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
