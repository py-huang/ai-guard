"""Production AI safety gateway: inbound/outbound Chain of Responsibility."""

from __future__ import annotations

from collections.abc import Sequence

from safety_gateway.audit.memory import InMemoryAuditLog
from safety_gateway.pii.demo_image import render_redacted_contact_book
from safety_gateway.pii.image import InMemoryImageRedactor
from safety_gateway.schemas import (
    ImageRedactRequest,
    ImageRedactResult,
    InboundRequest,
    OutboundRequest,
    SafetyProcessResult,
)
from safety_gateway.steps.base import BaseGuardStep, GuardContext
from safety_gateway.steps.content_safety import ContentSafetyStep
from safety_gateway.steps.parent_audit import ParentAuditStep
from safety_gateway.steps.socratic import SocraticPedagogyStep
from safety_gateway.steps.taiwan_pii import TaiwanPIIGuardStep
from safety_gateway.vault.base import BaseSessionVault
from safety_gateway.vault.memory import InMemorySessionVault


class AISafetyGateway:
    """Executes ordered inbound (pre-LLM) and outbound (post-LLM) guard steps.

    Default chain:
      inbound  : TaiwanPII -> ContentSafety -> SocraticPedagogy -> ParentAudit
      outbound : ContentSafety -> SocraticPedagogy -> ParentAudit -> TaiwanPII (deanonymize last)
    """

    def __init__(
        self,
        vault: BaseSessionVault | None = None,
        inbound_steps: Sequence[BaseGuardStep] | None = None,
        outbound_steps: Sequence[BaseGuardStep] | None = None,
        image_redactor: InMemoryImageRedactor | None = None,
        audit_log: InMemoryAuditLog | None = None,
    ) -> None:
        self._vault = vault or InMemorySessionVault()
        pii = _find_pii_step(inbound_steps) or TaiwanPIIGuardStep(vault=self._vault)
        self._pii = pii
        parent = _find_parent_step(inbound_steps) or _find_parent_step(outbound_steps)
        if parent is None:
            parent = ParentAuditStep(log=audit_log or InMemoryAuditLog())
        self._parent = parent
        socratic = _find_socratic_step(inbound_steps) or _find_socratic_step(outbound_steps)
        if socratic is None:
            socratic = SocraticPedagogyStep()
        safety = ContentSafetyStep()
        self._inbound_steps: tuple[BaseGuardStep, ...] = tuple(
            inbound_steps
            if inbound_steps is not None
            else (pii, safety, socratic, parent)
        )
        self._outbound_steps: tuple[BaseGuardStep, ...] = tuple(
            outbound_steps
            if outbound_steps is not None
            else (ContentSafetyStep(), socratic, parent, pii)
        )
        self._image_redactor = image_redactor or InMemoryImageRedactor(
            analyzer_engine=pii.analyzer
        )

    @property
    def vault(self) -> BaseSessionVault:
        return self._vault

    @property
    def audit_log(self) -> InMemoryAuditLog:
        return self._parent.log

    def process_inbound(self, session_id: str, text: str) -> SafetyProcessResult:
        request = InboundRequest(session_id=session_id, text=text)
        normalized = _normalize_fullwidth_alnum(request.text)
        context = GuardContext(
            session_id=request.session_id,
            text=normalized,
            original_text=normalized,
        )
        for step in self._inbound_steps:
            context = step.process_inbound(context)
        return _result(context, "inbound")

    def process_outbound(self, session_id: str, text: str) -> SafetyProcessResult:
        request = OutboundRequest(session_id=session_id, text=text)
        context = GuardContext(
            session_id=request.session_id,
            text=request.text,
            original_text=request.text,
        )
        for step in self._outbound_steps:
            context = step.process_outbound(context)
        return _result(context, "outbound")

    def deanonymize_text(self, session_id: str, text: str) -> str:
        return self._vault.deanonymize_text(session_id, text)

    def redact_image_in_memory(self, image_bytes: bytes) -> bytes:
        """Black out detected PII in an uploaded photo using RAM buffers only."""
        return self._image_redactor.redact_image_in_memory(image_bytes)

    def redact_image(self, session_id: str, image_bytes: bytes) -> ImageRedactResult:
        request = ImageRedactRequest(session_id=session_id, image_bytes=image_bytes)
        redacted = self.redact_image_in_memory(request.image_bytes)
        return ImageRedactResult(
            session_id=request.session_id,
            content_type="image/png",
            image_bytes=redacted,
            byte_size=len(redacted),
        )

    def demo_contact_book(self) -> tuple[bytes, bytes]:
        """Return (original, redacted) PNG of a drawn 聯絡簿 — no OCR required."""
        return render_redacted_contact_book()


def build_default_gateway(vault: BaseSessionVault | None = None) -> AISafetyGateway:
    return AISafetyGateway(vault=vault)


def _result(context: GuardContext, direction: str) -> SafetyProcessResult:
    return SafetyProcessResult(
        session_id=context.session_id,
        direction=direction,  # type: ignore[arg-type]
        original_text=context.original_text,
        processed_text=context.text,
        entities=list(context.entities),
        steps_executed=list(context.steps_executed),
        blocked=context.blocked,
        block_category=context.block_category,
        child_message=context.child_message,
    )


def _find_pii_step(steps: Sequence[BaseGuardStep] | None) -> TaiwanPIIGuardStep | None:
    return _find_step(steps, TaiwanPIIGuardStep)


def _find_parent_step(steps: Sequence[BaseGuardStep] | None) -> ParentAuditStep | None:
    return _find_step(steps, ParentAuditStep)


def _find_socratic_step(steps: Sequence[BaseGuardStep] | None) -> SocraticPedagogyStep | None:
    return _find_step(steps, SocraticPedagogyStep)


def _find_step(steps: Sequence[BaseGuardStep] | None, cls: type) -> object | None:
    if not steps:
        return None
    for step in steps:
        if isinstance(step, cls):
            return step
    return None


_FULLWIDTH_ALNUM = str.maketrans(
    {
        **{chr(0xFF10 + i): chr(ord("0") + i) for i in range(10)},
        **{chr(0xFF21 + i): chr(ord("A") + i) for i in range(26)},
        **{chr(0xFF41 + i): chr(ord("a") + i) for i in range(26)},
        0xFF0D: "-",
    }
)


def _normalize_fullwidth_alnum(text: str) -> str:
    """Fold fullwidth A-Z/a-z/0-9 so Taiwan IDs and phones match, keep CJK punctuation."""
    return text.translate(_FULLWIDTH_ALNUM)
