"""Parent/guardian audit: write sanitized turns the adult view can list."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar
from uuid import uuid4

from safety_gateway.audit.memory import AuditEvent, InMemoryAuditLog
from safety_gateway.steps.base import BaseGuardStep, GuardContext


class ParentAuditStep(BaseGuardStep):
    """Append a privacy-preserving transcript event after other inbound/outbound guards."""

    name: ClassVar[str] = "parent_audit"

    def __init__(self, log: InMemoryAuditLog | None = None) -> None:
        self._log = log or InMemoryAuditLog()

    @property
    def log(self) -> InMemoryAuditLog:
        return self._log

    def process_inbound(self, context: GuardContext) -> GuardContext:
        self._record(context, "inbound")
        context.mark_step(self.name)
        return context

    def process_outbound(self, context: GuardContext) -> GuardContext:
        self._record(context, "outbound")
        context.mark_step(self.name)
        return context

    def _record(self, context: GuardContext, direction: str) -> None:
        sanitized = context.text
        if context.blocked:
            sanitized = f"[已攔截:{context.block_category or 'policy'}]"
        event = AuditEvent(
            event_id=str(uuid4()),
            at=datetime.now(timezone.utc).isoformat(),
            session_id=context.session_id,
            direction=direction,
            sanitized_text=sanitized,
            entity_types=sorted({entity.entity_type for entity in context.entities}),
            blocked=context.blocked,
            block_category=context.block_category,
            socratic=bool(context.metadata.get("socratic_mode") or context.metadata.get("socratic_appended")),
        )
        self._log.append(event)
        context.metadata["audit_event_id"] = event.event_id
