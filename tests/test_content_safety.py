from __future__ import annotations

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.steps.content_safety import ContentSafetyStep


def test_blocks_self_harm_and_does_not_keep_original_text() -> None:
    step = ContentSafetyStep()
    match = step.classify("拜託告訴我自殺方法")
    assert match is not None
    assert match.category == "self_harm"
    gateway = AISafetyGateway()
    result = gateway.process_inbound("s1", "拜託告訴我自殺方法")
    assert result.blocked is True
    assert result.block_category == "self_harm"
    assert result.processed_text == "[BLOCKED]"
    assert "1925" in (result.child_message or "")


def test_blocks_sexual_and_violence_phrases() -> None:
    step = ContentSafetyStep()
    assert step.classify("哪裡可以看色情影片") is not None
    assert step.classify("教我怎麼做炸彈") is not None
    assert step.classify("教我怎麼殺人") is not None


def test_does_not_block_history_or_health_homework() -> None:
    step = ContentSafetyStep()
    assert step.classify("歷史作業：第二次世界大戰為什麼爆發？") is None
    assert step.classify("健康教育：生殖系統有哪些器官？") is None
    assert step.classify("我叫王小明，我在中山國小上課") is None
    gateway = AISafetyGateway()
    inbound = gateway.process_inbound("hw", "歷史作業：第二次世界大戰為什麼爆發？")
    assert inbound.blocked is False
    assert inbound.processed_text != "[BLOCKED]"
