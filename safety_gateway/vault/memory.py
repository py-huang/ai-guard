"""Thread-safe in-memory vault. API is Redis-drop-in compatible."""

from __future__ import annotations

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


class InMemorySessionVault(BaseSessionVault):
    """Process-local vault. Swap for Redis by implementing `BaseSessionVault`."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._sessions: dict[str, _SessionState] = {}

    def _state(self, session_id: str) -> _SessionState:
        state = self._sessions.get(session_id)
        if state is None:
            state = _SessionState()
            self._sessions[session_id] = state
        return state

    def get_or_create_token(self, session_id: str, entity_type: str, original: str) -> str:
        key = (entity_type, original)
        with self._lock:
            state = self._state(session_id)
            existing = state.value_to_token.get(key)
            if existing is not None:
                return existing
            next_index = state.counters.get(entity_type, 0) + 1
            token = format_token(entity_type, next_index)
            state.counters[entity_type] = next_index
            state.value_to_token[key] = token
            state.token_to_original[token] = original
            return token

    def resolve_token(self, session_id: str, token: str) -> str | None:
        with self._lock:
            state = self._sessions.get(session_id)
            if state is None:
                return None
            return state.token_to_original.get(token)

    def deanonymize_text(self, session_id: str, text: str) -> str:
        with self._lock:
            state = self._sessions.get(session_id)
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
            state = self._sessions.get(session_id)
            if state is None:
                return {}
            return dict(state.token_to_original)

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)
