"""In-memory guardian-readable audit log (sanitized by default)."""

from __future__ import annotations

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
    """Ring buffer of sanitized conversation events for the parent view."""

    def __init__(self, max_events: int = 200) -> None:
        self._max_events = max_events
        self._lock = Lock()
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        with self._lock:
            self._events.append(event)
            self._events = self._events[-self._max_events :]

    def list_session(self, session_id: str) -> list[AuditEvent]:
        with self._lock:
            return [event for event in self._events if event.session_id == session_id]

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._events = [event for event in self._events if event.session_id != session_id]
