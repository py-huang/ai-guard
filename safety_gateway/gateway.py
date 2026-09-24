"""Production AI safety gateway: inbound/outbound Chain of Responsibility."""

from __future__ import annotations

import io
from collections.abc import Sequence

from PIL import Image

from safety_gateway.audit.memory import InMemoryAuditLog
from safety_gateway.pii.demo_image import render_redacted_contact_book
from safety_gateway.pii.faces import (
    FaceDetector,
    count_faces_in_bytes,
    detect_faces_opencv,
    redact_face_boxes,
)
from safety_gateway.pii.image import InMemoryImageRedactor
from safety_gateway.pii.image_policy import classify_image_share, redaction_coverage
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
        face_detector: FaceDetector | None = None,
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
        self._face_detector = face_detector or detect_faces_opencv

    @property
    def vault(self) -> BaseSessionVault:
        return self._vault

    @property
    def audit_log(self) -> InMemoryAuditLog:
        return self._parent.log

    def process_inbound(
        self,
        session_id: str,
        text: str,
        image_bytes: bytes | None = None,
    ) -> SafetyProcessResult:
        request = InboundRequest(session_id=session_id, text=text)
        normalized = _normalize_fullwidth_alnum(request.text)
        had_image = bool(image_bytes)
        faces = count_faces_in_bytes(image_bytes or b"", self._face_detector) if had_image else 0
        context = GuardContext(
            session_id=request.session_id,
            text=normalized,
            original_text=normalized,
            metadata={"had_image": had_image, "faces_detected": faces},
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

    def prepare_llm_image(self, image_bytes: bytes) -> bytes:
        """Face + OCR redact before Gemini. Never send the child's original pixels."""
        try:
            return self.redact_image_in_memory(image_bytes)
        except Exception:
            return _face_redact_png(image_bytes, self._face_detector)

    def redact_image(self, session_id: str, image_bytes: bytes) -> ImageRedactResult:
        request = ImageRedactRequest(session_id=session_id, image_bytes=image_bytes)
        redacted, detected_entities = self._image_redactor.redact_image_with_entities(request.image_bytes)
        coverage = min(1.0, max(0.0, redaction_coverage(request.image_bytes, redacted)))
        blocked, block_reason = classify_image_share(coverage, detected_entities)
        return ImageRedactResult(
            session_id=request.session_id,
            content_type="image/png",
            image_bytes=redacted,
            byte_size=len(redacted),
            detected_entities=detected_entities,
            coverage=coverage,
            blocked=blocked,
            block_reason=block_reason,
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
        had_image=bool(context.metadata.get("had_image")),
        faces_detected=int(context.metadata.get("faces_detected") or 0),
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


def _face_redact_png(image_bytes: bytes, detector: FaceDetector) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as opened:
        opened.load()
        working = opened.convert("RGB")
    working = redact_face_boxes(working, detector(working))
    output = io.BytesIO()
    working.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _normalize_fullwidth_alnum(text: str) -> str:
    """Fold fullwidth A-Z/a-z/0-9 so Taiwan IDs and phones match, keep CJK punctuation."""
    return text.translate(_FULLWIDTH_ALNUM)
