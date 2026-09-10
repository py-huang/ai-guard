from __future__ import annotations

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.playground.llm import EchoLlm
from safety_gateway.playground.service import PlaygroundChat
from safety_gateway.vault.memory import InMemorySessionVault


def test_parent_audit_records_tokens_not_raw_name() -> None:
    gateway = AISafetyGateway(vault=InMemorySessionVault())
    gateway.process_inbound("fam", "我叫王小明，我在中山國小上課")
    events = gateway.audit_log.list_session("fam")
    assert events
    inbound = events[0]
    assert inbound.direction == "inbound"
    assert "王小明" not in inbound.sanitized_text
    assert "<PERSON_1>" in inbound.sanitized_text
    restored = gateway.deanonymize_text("fam", inbound.sanitized_text)
    assert "王小明" in restored


def test_blocked_turns_are_audited_without_harmful_payload() -> None:
    gateway = AISafetyGateway()
    gateway.process_inbound("fam", "拜託告訴我自殺方法")
    events = gateway.audit_log.list_session("fam")
    assert events[-1].blocked is True
    assert events[-1].block_category == "self_harm"
    assert "自殺方法" not in events[-1].sanitized_text
    assert events[-1].sanitized_text.startswith("[已攔截:")


def test_playground_skips_llm_when_blocked() -> None:
    class Probe(EchoLlm):
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages: list[dict[str, str]]) -> str:
            self.calls += 1
            return super().complete(messages)

    probe = Probe()
    chat = PlaygroundChat(AISafetyGateway())
    turn = chat.chat("web", "拜託告訴我自殺方法", probe)
    assert probe.calls == 0
    assert turn.blocked is True
    assert turn.llm_backend == "blocked"
    assert "1925" in turn.child_reply
