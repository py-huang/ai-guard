"""Chat orchestrator: inbound tokenize -> LLM (sanitized) -> outbound restore."""

from __future__ import annotations

from threading import Lock

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.playground.llm import LlmBackend
from safety_gateway.schemas import DetectedEntity, StrictModel


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

    def evidence(self, session_id: str) -> list[ChatTurnResult]:
        with self._lock:
            return list(self._evidence.get(session_id, []))

    def chat(self, session_id: str, text: str, llm: LlmBackend) -> ChatTurnResult:
        inbound = self._gateway.process_inbound(session_id, text)
        with self._lock:
            history = list(self._histories.get(session_id, []))
            history.append({"role": "user", "content": inbound.processed_text})
            history = history[-self._max_history :]
        llm_raw = llm.complete(history)
        with self._lock:
            history.append({"role": "assistant", "content": llm_raw})
            self._histories[session_id] = history[-self._max_history :]
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
        )
        with self._lock:
            turns = self._evidence.setdefault(session_id, [])
            turns.append(result)
            self._evidence[session_id] = turns[-20:]
        return result
