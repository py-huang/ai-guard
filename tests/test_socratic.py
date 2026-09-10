from __future__ import annotations

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.steps.socratic import INBOUND_PREFIX, SocraticPedagogyStep


def test_homework_dump_is_wrapped_inbound_and_gets_a_question_outbound() -> None:
    gateway = AISafetyGateway()
    inbound = gateway.process_inbound("s", "這題數學作業直接給我標準答案：12加35")
    assert inbound.blocked is False
    assert inbound.processed_text.startswith("【教學模式】")
    assert "標準答案" in inbound.processed_text
    outbound = gateway.process_outbound("s", "12加35等於47。")
    assert "你先試試看" in outbound.processed_text
    assert outbound.processed_text.rstrip().endswith("？") or "？" in outbound.processed_text


def test_plain_introduction_is_not_wrapped() -> None:
    step = SocraticPedagogyStep()
    assert step.looks_like_answer_dump("我叫王小明，我在中山國小上課") is False
    gateway = AISafetyGateway()
    inbound = gateway.process_inbound("s", "我叫王小明，我在中山國小上課")
    assert not inbound.processed_text.startswith(INBOUND_PREFIX[:6])
    assert "<PERSON_1>" in inbound.processed_text
