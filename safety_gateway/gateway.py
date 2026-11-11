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
from safety_gateway.steps.content_model import ContentModel
from safety_gateway.steps.content_safety import ContentSafetyStep
from safety_gateway.steps.parent_audit import ParentAuditStep
from safety_gateway.steps.socratic import INBOUND_PREFIX as SOCRATIC_INBOUND_PREFIX
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
        content_model: ContentModel | None = None,
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
        safety = _find_safety_step(inbound_steps) or ContentSafetyStep(model=content_model)
        # Re-check chain: PII tokenization + content safety only. No Socratic prefix and
        # no audit event, so a server can re-verify text it already processed once.
        self._safety = safety
        self._sanitize_steps: tuple[BaseGuardStep, ...] = (pii, safety)
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
    def safety_step(self) -> ContentSafetyStep:
        return self._safety

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

    def sanitize_text(self, session_id: str, text: str) -> SafetyProcessResult:
        """Idempotent pre-LLM check used for server-side enforcement.

        Runs only PII tokenization and content safety. Unlike ``process_inbound`` it
        neither prefixes the Socratic instruction nor writes a parent-audit event, so it
        is safe to call on text that was already inspected (history, model output).
        Running it twice on its own output returns the same text.
        """
        request = InboundRequest(session_id=session_id, text=text)
        normalized = _normalize_fullwidth_alnum(request.text)
        # Our own Socratic instruction contains "蘇格拉底", which the name recognizer would
        # happily tokenize. Keep that trusted prefix out of the scan and put it back after.
        prefix = SOCRATIC_INBOUND_PREFIX if normalized.startswith(SOCRATIC_INBOUND_PREFIX) else ""
        body = normalized[len(prefix) :]
        context = GuardContext(
            session_id=request.session_id,
            text=body,
            original_text=body,
            metadata={"had_image": False, "faces_detected": 0},
        )
        for step in self._sanitize_steps:
            context = step.process_inbound(context)
        if prefix and not context.blocked:
            context.text = prefix + context.text
            context.original_text = prefix + context.original_text
        return _result(context, "inbound")

    def moderate_output(self, session_id: str, text: str) -> SafetyProcessResult:
        """Content-safety check on model output only.

        Deliberately no PII tokenization: the model only ever saw placeholders, and the
        name recognizer would turn ordinary words in a reply (e.g. 蘇格拉底) into tokens.
        No audit event and no Socratic hint either; callers add those if they want them.
        """
        request = OutboundRequest(session_id=session_id, text=text)
        context = GuardContext(
            session_id=request.session_id,
            text=request.text,
            original_text=request.text,
        )
        context = self._safety.process_outbound(context)
        return _result(context, "outbound")

    def reset_session(self, session_id: str) -> None:
        """Forget everything held for one session (vault mappings and audit events)."""
        self._vault.clear_session(session_id)
        self._parent.log.clear_session(session_id)

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
        ocr_text = ""
        try:
            from safety_gateway.pii.ocr import ocr_lines

            ocr_text = " ".join(ocr_lines(request.image_bytes))
        except Exception:
            ocr_text = ""
        blocked, block_reason = classify_image_share(coverage, detected_entities, ocr_text=ocr_text)
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


def _find_safety_step(steps: Sequence[BaseGuardStep] | None) -> ContentSafetyStep | None:
    return _find_step(steps, ContentSafetyStep)


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
