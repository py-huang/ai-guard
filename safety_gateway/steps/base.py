"""Pipeline context and Chain-of-Responsibility step interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar

from safety_gateway.schemas import DetectedEntity


@dataclass
class GuardContext:
    session_id: str
    text: str
    original_text: str
    entities: list[DetectedEntity] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    steps_executed: list[str] = field(default_factory=list)

    def mark_step(self, name: str) -> None:
        self.steps_executed.append(name)


class BaseGuardStep(ABC):
    """One handler in the inbound (pre-LLM) or outbound (post-LLM) chain."""

    name: ClassVar[str]

    @abstractmethod
    def process_inbound(self, context: GuardContext) -> GuardContext:
        """Transform child input before it is sent to the model."""

    @abstractmethod
    def process_outbound(self, context: GuardContext) -> GuardContext:
        """Transform model output before it is shown to the child."""
