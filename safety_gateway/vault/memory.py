"""Thread-safe in-memory vault. API is Redis-drop-in compatible.

Originals of a child's PII live here, so the vault is bounded on purpose:

* ``ttl_seconds``  - a session that has not been touched for this long is dropped.
* ``max_sessions`` - least-recently-used sessions are evicted past this count.

Both default to ``None`` (unbounded) so unit tests and demos behave as before. The
production server always passes real limits (see ``safety_gateway.server.settings``).
"""

from __future__ import annotations

import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from threading import RLock

from safety_gateway.vault.base import BaseSessionVault


def format_token(entity_type: str, index: int) -> str:
    return f"<{entity_type}_{index}>"


@dataclass
class _SessionState:
    token_to_original: dict[str, str] = field(default_factory=dict)
    value_to_token: dict[tuple[str, str], str] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)
    touched_at: float = 0.0


class InMemorySessionVault(BaseSessionVault):
    """Process-local vault. Swap for Redis by implementing `BaseSessionVault`."""

    def __init__(
        self,
        ttl_seconds: float | None = None,
        max_sessions: int | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        if max_sessions is not None and max_sessions < 1:
            raise ValueError("max_sessions must be at least 1")
        self._lock = RLock()
        self._ttl = ttl_seconds
        self._max_sessions = max_sessions
        self._clock = clock
        # Ordered from least to most recently used.
        self._sessions: OrderedDict[str, _SessionState] = OrderedDict()

    @property
    def session_count(self) -> int:
        with self._lock:
            self._prune_locked()
            return len(self._sessions)

    def _prune_locked(self) -> None:
        if self._ttl is not None:
            cutoff = self._clock() - self._ttl
            while self._sessions:
                oldest_id = next(iter(self._sessions))
                if self._sessions[oldest_id].touched_at > cutoff:
                    break
                del self._sessions[oldest_id]
        if self._max_sessions is not None:
            while len(self._sessions) > self._max_sessions:
                self._sessions.popitem(last=False)

    def _lookup_locked(self, session_id: str, *, create: bool) -> _SessionState | None:
        self._prune_locked()
        state = self._sessions.get(session_id)
        if state is None:
            if not create:
                return None
            state = _SessionState()
            self._sessions[session_id] = state
        state.touched_at = self._clock()
        self._sessions.move_to_end(session_id)
        self._prune_locked()
        return state

    def get_or_create_token(self, session_id: str, entity_type: str, original: str) -> str:
        key = (entity_type, original)
        with self._lock:
            state = self._lookup_locked(session_id, create=True)
            assert state is not None
            existing = state.value_to_token.get(key)
            if existing is not None:
                return existing
            next_index = state.counters.get(entity_type, 0) + 1
            token = format_token(entity_type, next_index)
            state.counters[entity_type] = next_index
            state.value_to_token[key] = token
            state.token_to_original[token] = original
            return token

    def alias_value(self, session_id: str, entity_type: str, alias: str, canonical: str) -> str:
        token = self.get_or_create_token(session_id, entity_type, canonical)
        if alias == canonical:
            return token
        with self._lock:
            state = self._lookup_locked(session_id, create=True)
            assert state is not None
            state.value_to_token[(entity_type, alias)] = token
        return token

    def resolve_token(self, session_id: str, token: str) -> str | None:
        with self._lock:
            state = self._lookup_locked(session_id, create=False)
            if state is None:
                return None
            return state.token_to_original.get(token)

    def deanonymize_text(self, session_id: str, text: str) -> str:
        with self._lock:
            state = self._lookup_locked(session_id, create=False)
            if state is None or not state.token_to_original:
                return text
            mappings = tuple(
                sorted(state.token_to_original.items(), key=lambda item: len(item[0]), reverse=True)
            )
        restored = text
        for token, original in mappings:
            restored = restored.replace(token, original)
        return restored

    def list_mappings(self, session_id: str) -> dict[str, str]:
        with self._lock:
            state = self._lookup_locked(session_id, create=False)
            if state is None:
                return {}
            return dict(state.token_to_original)

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def clear_all(self) -> None:
        with self._lock:
            self._sessions.clear()
