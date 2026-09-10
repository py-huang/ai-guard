"""Stub: future K-12 content moderation / blocked-topic filtering."""

from __future__ import annotations

from typing import ClassVar

from safety_gateway.steps.base import BaseGuardStep, GuardContext


class ContentSafetyStep(BaseGuardStep):
    """Placeholder for policy classifiers (self-harm, sexual content, hate, etc.)."""

    name: ClassVar[str] = "content_safety"

    def process_inbound(self, context: GuardContext) -> GuardContext:
        context.metadata.setdefault("pending_modules", []).append(self.name)
        context.mark_step(self.name)
        return context

    def process_outbound(self, context: GuardContext) -> GuardContext:
        context.metadata.setdefault("pending_modules", []).append(f"{self.name}:outbound")
        context.mark_step(self.name)
        return context
