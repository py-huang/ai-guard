from __future__ import annotations

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.playground.llm import EchoLlm
from safety_gateway.playground.service import PlaygroundChat
from safety_gateway.vault.memory import InMemorySessionVault


def test_playground_chat_hides_pii_from_llm_and_restores_for_child() -> None:
    vault = InMemorySessionVault()
    chat = PlaygroundChat(AISafetyGateway(vault=vault))
    turn = chat.chat("web-1", "我叫王小明，我在中山國小上課", EchoLlm())
    assert "王小明" not in turn.sent_to_llm
    assert "<PERSON_1>" in turn.sent_to_llm
    assert "<SCHOOL_1>" in turn.sent_to_llm
    assert "王小明" in turn.child_reply
    assert "<PERSON_1>" not in turn.child_reply
    assert turn.llm_backend == "echo"
    assert turn.pii_leaked_to_llm is False
    log = chat.evidence("web-1")
    assert len(log) == 1
    assert log[0].sent_to_llm == turn.sent_to_llm


def test_playground_wraps_homework_before_llm() -> None:
    chat = PlaygroundChat(AISafetyGateway(vault=InMemorySessionVault()))
    turn = chat.chat("web-2", "這題數學作業直接給我標準答案：12加35", EchoLlm())
    assert turn.sent_to_llm.startswith("【教學模式】")
    assert "標準答案" in turn.sent_to_llm
    assert "你會先從哪裡開始" in turn.child_reply
    assert turn.blocked is False
