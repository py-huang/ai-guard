"""Stub: future parent/guardian audit log of sanitized conversation turns."""

from __future__ import annotations

from typing import ClassVar

from safety_gateway.steps.base import BaseGuardStep, GuardContext


class ParentAuditStep(BaseGuardStep):
    """Placeholder for appending a privacy-preserving transcript event for guardians."""

    name: ClassVar[str] = "parent_audit"

    def process_inbound(self, context: GuardContext) -> GuardContext:
        context.metadata.setdefault("pending_modules", []).append(self.name)
        context.mark_step(self.name)
        return context

    def process_outbound(self, context: GuardContext) -> GuardContext:
        context.metadata.setdefault("pending_modules", []).append(f"{self.name}:outbound")
        context.mark_step(self.name)
        return context
