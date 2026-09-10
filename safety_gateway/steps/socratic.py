"""Stub: future Socratic / guided-question pedagogy policy for K-12 tutoring."""

from __future__ import annotations

from typing import ClassVar

from safety_gateway.steps.base import BaseGuardStep, GuardContext


class SocraticPedagogyStep(BaseGuardStep):
    """Placeholder for rewriting answers into scaffolded questions instead of spoilers."""

    name: ClassVar[str] = "socratic_pedagogy"

    def process_inbound(self, context: GuardContext) -> GuardContext:
        context.metadata.setdefault("pending_modules", []).append(self.name)
        context.mark_step(self.name)
        return context

    def process_outbound(self, context: GuardContext) -> GuardContext:
        context.metadata.setdefault("pending_modules", []).append(f"{self.name}:outbound")
        context.mark_step(self.name)
        return context
