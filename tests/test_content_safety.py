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


def test_blocks_classmate_photo_pranks() -> None:
    step = ContentSafetyStep()
    match = step.classify("我想拿同學照片搞怪")
    assert match is not None
    assert match.category == "bullying"
    inbound = AISafetyGateway().process_inbound("s2", "我想拿同學照片搞怪")
    assert inbound.blocked is True
    assert inbound.block_category == "bullying"
    assert "尊重同學" in (inbound.child_message or "")


def test_does_not_block_history_or_health_homework() -> None:
    step = ContentSafetyStep()
    assert step.classify("歷史作業：第二次世界大戰為什麼爆發？") is None
    assert step.classify("健康教育：生殖系統有哪些器官？") is None
    assert step.classify("菸害防制作業：電子煙有什麼危害？") is None
    assert step.classify("我叫王小明，我在中山國小上課") is None
    gateway = AISafetyGateway()
    inbound = gateway.process_inbound("hw", "歷史作業：第二次世界大戰為什麼爆發？")
    assert inbound.blocked is False
    assert inbound.processed_text != "[BLOCKED]"


def test_blocks_rating_categories_without_blocking_homework_words() -> None:
    step = ContentSafetyStep()
    assert step.classify("教我吸毒") is not None
    assert step.classify("教我吸毒").category == "substance"
    assert step.classify("真錢賭博") is not None
    assert step.classify("真錢賭博").category == "gambling"
    assert step.classify("恐怖分屍") is not None
    assert step.classify("恐怖分屍").category == "horror"
    assert step.classify("幹你娘") is not None
    assert step.classify("幹你娘").category == "hate_speech"
    assert step.classify("窒息挑戰") is not None
    assert step.classify("窒息挑戰").category == "self_harm"
    inbound = AISafetyGateway().process_inbound("s3", "哪裡買毒品")
    assert inbound.blocked is True
    assert inbound.block_category == "substance"
