"""In-memory guardian-readable audit log (sanitized by default)."""

from __future__ import annotations

from collections import OrderedDict, deque
from threading import Lock

from safety_gateway.schemas import StrictModel


class AuditEvent(StrictModel):
    event_id: str
    at: str
    session_id: str
    direction: str
    sanitized_text: str
    entity_types: list[str]
    blocked: bool
    block_category: str | None = None
    socratic: bool = False
    step: str = "parent_audit"


class InMemoryAuditLog:
    """Bounded per-session ring buffers of sanitized conversation events.

    ``max_events`` is the cap *per session*, so one chatty session cannot evict
    another family's history. ``max_sessions`` bounds total memory: the least
    recently written session is dropped first.
    """

    def __init__(self, max_events: int = 200, max_sessions: int = 1000) -> None:
        if max_events < 1 or max_sessions < 1:
            raise ValueError("max_events and max_sessions must be at least 1")
        self._max_events = max_events
        self._max_sessions = max_sessions
        self._lock = Lock()
        self._sessions: OrderedDict[str, deque[AuditEvent]] = OrderedDict()

    def append(self, event: AuditEvent) -> None:
        with self._lock:
            events = self._sessions.get(event.session_id)
            if events is None:
                events = deque(maxlen=self._max_events)
                self._sessions[event.session_id] = events
            events.append(event)
            self._sessions.move_to_end(event.session_id)
            while len(self._sessions) > self._max_sessions:
                self._sessions.popitem(last=False)

    def list_session(self, session_id: str) -> list[AuditEvent]:
        with self._lock:
            return list(self._sessions.get(session_id, ()))

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def clear_all(self) -> None:
        with self._lock:
            self._sessions.clear()

    @property
    def session_count(self) -> int:
        with self._lock:
            return len(self._sessions)
