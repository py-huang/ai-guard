"""Chat orchestrator: inbound tokenize -> LLM (sanitized) -> outbound restore."""

from __future__ import annotations

import base64
from threading import Lock

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.image import images_differ
from safety_gateway.playground.llm import (
    LlmBackend,
    LlmBusyError,
    LlmError,
    LlmPolicyBlockError,
    LlmQuotaError,
)
from safety_gateway.playground.zhuyin import ZhuyinPart, to_zhuyin_parts
from safety_gateway.schemas import DetectedEntity, StrictModel
from safety_gateway.steps.homework_image import (
    GENERATE_CAPTION,
    REFUSE_MESSAGE,
    image_gen_action,
    imagen_prompt,
)


class ChatTurnResult(StrictModel):
    session_id: str
    child_reply: str
    original_text: str
    sent_to_llm: str
    llm_raw: str
    llm_backend: str
    llm_model: str
    entities: list[DetectedEntity]
    inbound_steps: list[str]
    outbound_steps: list[str]
    pii_leaked_to_llm: bool
    leaked_values: list[str]
    blocked: bool = False
    block_category: str | None = None
    had_image: bool = False
    faces_detected: int = 0
    image_sent_to_llm: bool = False
    image_generated: bool = False
    generated_image_base64: str | None = None
    image_redacted: bool = False
    redacted_image_base64: str | None = None
    zhuyin_parts: list[ZhuyinPart] = []


class PlaygroundChat:
    def __init__(self, gateway: AISafetyGateway, max_history: int = 12) -> None:
        self._gateway = gateway
        self._max_history = max_history
        self._lock = Lock()
        self._histories: dict[str, list[dict[str, str]]] = {}
        self._evidence: dict[str, list[ChatTurnResult]] = {}

    def reset(self, session_id: str) -> None:
        with self._lock:
            self._histories.pop(session_id, None)
            self._evidence.pop(session_id, None)
        self._gateway.vault.clear_session(session_id)
        self._gateway.audit_log.clear_session(session_id)

    def evidence(self, session_id: str) -> list[ChatTurnResult]:
        with self._lock:
            return list(self._evidence.get(session_id, []))

    def chat(
        self,
        session_id: str,
        text: str,
        llm: LlmBackend,
        image_bytes: bytes | None = None,
        enable_images: bool = False,
    ) -> ChatTurnResult:
        if not enable_images:
            image_bytes = None
        inbound = self._gateway.process_inbound(session_id, text, image_bytes=image_bytes)
        llm_image: bytes | None = None
        image_redacted = False
        redacted_b64: str | None = None
        if image_bytes:
            try:
                llm_image = self._gateway.prepare_llm_image(image_bytes)
            except Exception:
                llm_image = None
            if llm_image and (
                inbound.faces_detected > 0 or images_differ(image_bytes, llm_image)
            ):
                image_redacted = True
                redacted_b64 = base64.b64encode(llm_image).decode("ascii")

        def emit(result: ChatTurnResult) -> ChatTurnResult:
            result.image_redacted = image_redacted
            result.redacted_image_base64 = redacted_b64 if image_redacted else None
            result.zhuyin_parts = to_zhuyin_parts(result.child_reply)
            self._store_evidence(session_id, result)
            return result

        if inbound.blocked:
            result = ChatTurnResult(
                session_id=session_id,
                child_reply=inbound.child_message or "這件事不適合在這裡討論。",
                original_text=inbound.original_text,
                sent_to_llm=inbound.processed_text,
                llm_raw="",
                llm_backend="blocked",
                llm_model="none",
                entities=list(inbound.entities),
                inbound_steps=list(inbound.steps_executed),
                outbound_steps=[],
                pii_leaked_to_llm=False,
                leaked_values=[],
                blocked=True,
                block_category=inbound.block_category,
                had_image=inbound.had_image,
                faces_detected=inbound.faces_detected,
                image_sent_to_llm=False,
            )
            return emit(result)

        action = image_gen_action(inbound.processed_text) if enable_images else "chat"
        if action == "refuse":
            outbound = self._gateway.process_outbound(session_id, REFUSE_MESSAGE)
            result = ChatTurnResult(
                session_id=session_id,
                child_reply=outbound.processed_text,
                original_text=inbound.original_text,
                sent_to_llm=inbound.processed_text,
                llm_raw="",
                llm_backend="image_gen",
                llm_model="denied",
                entities=list(inbound.entities),
                inbound_steps=list(inbound.steps_executed),
                outbound_steps=list(outbound.steps_executed),
                pii_leaked_to_llm=False,
                leaked_values=[],
                had_image=inbound.had_image,
                faces_detected=inbound.faces_detected,
                image_sent_to_llm=False,
                image_generated=False,
            )
            return emit(result)
        if action == "generate":
            try:
                png, model = llm.generate_image(imagen_prompt(inbound.processed_text))
                caption = GENERATE_CAPTION
            except LlmPolicyBlockError as exc:
                result = ChatTurnResult(
                    session_id=session_id,
                    child_reply=exc.child_message,
                    original_text=inbound.original_text,
                    sent_to_llm=inbound.processed_text,
                    llm_raw="",
                    llm_backend="blocked",
                    llm_model=llm.model,
                    entities=list(inbound.entities),
                    inbound_steps=list(inbound.steps_executed),
                    outbound_steps=[],
                    pii_leaked_to_llm=False,
                    leaked_values=[],
                    blocked=True,
                    block_category="llm_safety",
                    had_image=inbound.had_image,
                    faces_detected=inbound.faces_detected,
                    image_sent_to_llm=False,
                    image_generated=False,
                )
                return emit(result)
            except (LlmQuotaError, LlmBusyError, LlmError) as exc:
                outbound = self._gateway.process_outbound(session_id, exc.child_message)
                model = "quota" if isinstance(exc, LlmQuotaError) else "unavailable"
                result = ChatTurnResult(
                    session_id=session_id,
                    child_reply=outbound.processed_text,
                    original_text=inbound.original_text,
                    sent_to_llm=inbound.processed_text,
                    llm_raw="",
                    llm_backend="image_gen",
                    llm_model=model,
                    entities=list(inbound.entities),
                    inbound_steps=list(inbound.steps_executed),
                    outbound_steps=list(outbound.steps_executed),
                    pii_leaked_to_llm=False,
                    leaked_values=[],
                    had_image=inbound.had_image,
                    faces_detected=inbound.faces_detected,
                    image_sent_to_llm=False,
                    image_generated=False,
                )
                return emit(result)
            outbound = self._gateway.process_outbound(session_id, caption)
            result = ChatTurnResult(
                session_id=session_id,
                child_reply=outbound.processed_text,
                original_text=inbound.original_text,
                sent_to_llm=inbound.processed_text,
                llm_raw="",
                llm_backend=llm.name,
                llm_model=model,
                entities=list(inbound.entities),
                inbound_steps=list(inbound.steps_executed),
                outbound_steps=list(outbound.steps_executed),
                pii_leaked_to_llm=False,
                leaked_values=[],
                had_image=inbound.had_image,
                faces_detected=inbound.faces_detected,
                image_sent_to_llm=False,
                image_generated=True,
                generated_image_base64=base64.b64encode(png).decode("ascii"),
            )
            return emit(result)

        with self._lock:
            history = list(self._histories.get(session_id, []))
            pending = history + [{"role": "user", "content": inbound.processed_text}]
            pending = pending[-self._max_history :]
        try:
            llm_raw = llm.complete(pending, image_bytes=llm_image)
        except LlmPolicyBlockError as exc:
            result = ChatTurnResult(
                session_id=session_id,
                child_reply=exc.child_message,
                original_text=inbound.original_text,
                sent_to_llm=inbound.processed_text,
                llm_raw="",
                llm_backend="blocked",
                llm_model=llm.model,
                entities=list(inbound.entities),
                inbound_steps=list(inbound.steps_executed),
                outbound_steps=[],
                pii_leaked_to_llm=False,
                leaked_values=[],
                blocked=True,
                block_category="llm_safety",
                had_image=inbound.had_image,
                faces_detected=inbound.faces_detected,
                image_sent_to_llm=False,
            )
            return emit(result)
        with self._lock:
            pending.append({"role": "assistant", "content": llm_raw})
            self._histories[session_id] = pending[-self._max_history :]
        outbound = self._gateway.process_outbound(session_id, llm_raw)
        originals = [entity.original for entity in inbound.entities]
        exposed = inbound.processed_text + "\n" + llm_raw
        leaked = [value for value in originals if value and value in exposed]
        result = ChatTurnResult(
            session_id=session_id,
            child_reply=outbound.processed_text,
            original_text=inbound.original_text,
            sent_to_llm=inbound.processed_text,
            llm_raw=llm_raw,
            llm_backend=llm.name,
            llm_model=llm.model,
            entities=list(inbound.entities),
            inbound_steps=list(inbound.steps_executed),
            outbound_steps=list(outbound.steps_executed),
            pii_leaked_to_llm=bool(leaked),
            leaked_values=leaked,
            blocked=outbound.blocked,
            block_category=outbound.block_category,
            had_image=inbound.had_image,
            faces_detected=inbound.faces_detected,
            image_sent_to_llm=bool(llm_image),
        )
        if outbound.blocked:
            result.child_reply = outbound.child_message or result.child_reply
        return emit(result)

    def _store_evidence(self, session_id: str, result: ChatTurnResult) -> None:
        stored = result.model_copy(
            update={"generated_image_base64": None, "redacted_image_base64": None}
        )
        with self._lock:
            turns = self._evidence.setdefault(session_id, [])
            turns.append(stored)
            self._evidence[session_id] = turns[-20:]
