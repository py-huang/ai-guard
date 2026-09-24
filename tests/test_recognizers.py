from __future__ import annotations

import pytest

from safety_gateway.nlp import spacy_zh_available
from safety_gateway.pii.analyzer import build_analyzer_engine


def _types(text: str) -> set[str]:
    engine = build_analyzer_engine()
    return {hit.entity_type for hit in engine.analyze(text=text, language="zh")}


def test_phone_mobile_and_landline() -> None:
    text = "手機 0912-345-678，家裡 02-2345-6789，備用 0912345678"
    types = _types(text)
    assert "PHONE_NUMBER" in types


def test_valid_tw_id_detected_invalid_ignored() -> None:
    engine = build_analyzer_engine()
    valid = engine.analyze(text="身分證 A123456789", language="zh")
    invalid = engine.analyze(text="身分證 A123456780", language="zh")
    assert any(hit.entity_type == "TW_ID" for hit in valid)
    assert all(hit.entity_type != "TW_ID" for hit in invalid)


def test_school_and_location_and_person() -> None:
    text = "我叫王小明，就讀中山國小，住在台北市中正區重慶南路一段122號2樓"
    types = _types(text)
    assert {"PERSON", "SCHOOL", "LOCATION"} <= types


def test_contact_book_labels_and_simplified_hao() -> None:
    types = _types("姓名：王小明，學校中山國小，台北市中正區重南路一段122号")
    assert "PERSON" in types
    assert "SCHOOL" in types
    assert "LOCATION" in types


def test_homework_question_without_pii_is_clean() -> None:
    assert _types("恐龍為什麼會滅絕？") == set()


def test_self_intro_with_class_particle_and_seat_number() -> None:
    text = "我是五年二班的陳大同，座號 12 號，幫我寫一篇自我介紹。"
    types = _types(text)
    assert {"PERSON", "SCHOOL_CLASS"} <= types, types
    assert "STUDENT_ID" not in types
    engine = build_analyzer_engine()
    spans = {text[hit.start : hit.end] for hit in engine.analyze(text=text, language="zh")}
    assert {"陳大同", "五年二班"} <= spans
    assert "12" not in spans


def test_homeroom_teacher_and_school_are_redacted() -> None:
    text = "我在信義國小上學，我的班導師叫張美麗。"
    types = _types(text)
    assert {"SCHOOL", "PERSON"} <= types, types
    engine = build_analyzer_engine()
    spans = {text[hit.start : hit.end] for hit in engine.analyze(text=text, language="zh")}
    assert {"信義國小", "張美麗"} <= spans


def test_leave_slip_identifies_class_name_and_student_id() -> None:
    text = "幫我寫一張請假單：我是三年一班林小華，學號 109012，明天因為感冒要請假。"
    types = _types(text)
    assert {"PERSON", "SCHOOL_CLASS", "STUDENT_ID"} <= types, types
    engine = build_analyzer_engine()
    spans = {text[hit.start : hit.end] for hit in engine.analyze(text=text, language="zh")}
    assert {"林小華", "三年一班", "109012"} <= spans


def test_instagram_handle_in_follow_request() -> None:
    samples = (
        "我的 IG 帳號是 xiao_ming_2015，你可以追蹤我嗎？",
        "我的 IG 是 xiao_ming_2015，你可以追蹤我嗎？",
        "IG帳號 @xiao_ming_2015",
    )
    for text in samples:
        types = _types(text)
        assert "IG_HANDLE" in types, text
        engine = build_analyzer_engine()
        values = {text[hit.start : hit.end] for hit in engine.analyze(text=text, language="zh") if hit.entity_type == "IG_HANDLE"}
        assert any("xiao_ming_2015" in item for item in values), text
    assert "IG_HANDLE" not in _types("IG 是什麼？")


def test_student_id_needs_label() -> None:
    assert "STUDENT_ID" not in _types("這題答案是 109012")


def test_pii_inside_child_questions_is_detected() -> None:
    samples = {
        "請問王小明的數學作業怎麼寫？": {"PERSON"},
        "中山國小附近有什麼博物館？": {"SCHOOL"},
        "我的電話是 0912-345-678，可以幫我記作業嗎？": {"PHONE_NUMBER"},
        "我住台北市中山區，今天想問火山": {"LOCATION"},
        "信箱是 ming@school.edu.tw 作業要寄到哪？": {"EMAIL_ADDRESS"},
        "身分證 A123456789 這題怎麼算？": {"TW_ID"},
        "John Smith 同學的英文名字怎麼唸？": {"PERSON"},
        "林小華 同學明天請假，作業怎麼辦？": {"PERSON"},
    }
    for text, expected in samples.items():
        assert expected <= _types(text), text


def test_traditional_chinese_classmate_cues() -> None:
    samples = (
        "這是林小華",
        "她叫林小華",
        "班上的林小華今天沒來",
        "這是同學林小華的照片",
        "名牌：林小華",
        "把林小華的照片拿來搞怪",
    )
    for text in samples:
        assert "PERSON" in _types(text), text


def test_honorific_and_together_with_name_are_person() -> None:
    samples = (
        "我跟周品難先生今天會繼續一起搭公車下班嗎，你用塔羅牌幫我測看看",
        "林小華小姐明天請假",
        "我和陳大同老師下課後要不要一起走",
    )
    engine = build_analyzer_engine()
    for text in samples:
        assert "PERSON" in _types(text), text
        spans = {text[hit.start : hit.end] for hit in engine.analyze(text=text, language="zh") if hit.entity_type == "PERSON"}
        assert any(name in spans for name in ("周品難", "林小華", "陳大同")), (text, spans)


def test_does_not_treat_common_words_as_names() -> None:
    types = _types("今天作業寫在黑板上，我們可以一起想")
    assert "PERSON" not in types


def test_presidio_defaults_in_chinese_sentence() -> None:
    types = _types(
        "信箱是 ming@school.edu.tw，信用卡 4111111111111111，"
        "美國社會安全碼 856-45-6789，網址 https://www.moe.gov.tw"
    )
    assert {"EMAIL_ADDRESS", "CREDIT_CARD", "US_SSN", "URL"} <= types


def test_taiwan_counterparts_of_presidio_ideas() -> None:
    types = _types(
        "我叫 John Smith，護照號碼 A12345678，駕照號碼 B223456789，"
        "郵局帳號 1234567890123，生日民國102年3月2日，媽媽在長庚醫院上班"
    )
    assert {
        "PERSON",
        "TW_PASSPORT",
        "TW_DRIVER_LICENSE",
        "TW_BANK_ACCOUNT",
        "DATE_TIME",
        "ORGANIZATION",
    } <= types


def test_gregorian_cjk_date() -> None:
    assert "DATE_TIME" in _types("生日是 2013年3月2日")


def test_homework_not_over_redacted() -> None:
    types = _types("今天作業寫在黑板上，3月有健康教育，12 加 35 等於多少？")
    assert "PERSON" not in types
    assert "CREDIT_CARD" not in types
    assert "US_SSN" not in types
    assert "DATE_TIME" not in types
    assert "TW_BANK_ACCOUNT" not in types
    assert "ORGANIZATION" not in types


def test_national_id_is_not_passport() -> None:
    engine = build_analyzer_engine()
    hits = engine.analyze(text="身分證 A123456789", language="zh")
    types = {hit.entity_type for hit in hits}
    assert "TW_ID" in types
    assert "TW_PASSPORT" not in types


def test_generic_company_phrase_is_not_organization() -> None:
    assert "ORGANIZATION" not in _types("功課問：什麼是股份有限公司？")


@pytest.mark.skipif(not spacy_zh_available(), reason="zh_core_web_md is not installed")
def test_spacy_zh_person_without_name_cue() -> None:
    engine = build_analyzer_engine()
    hits = engine.analyze(text="王小明明天去上學", language="zh")
    types = {hit.entity_type for hit in hits}
    assert "PERSON" in types
    assert "DATE_TIME" not in types
    assert any(hit.entity_type == "PERSON" and "王小明" in "王小明明天去上學"[hit.start:hit.end] for hit in hits)


@pytest.mark.skipif(not spacy_zh_available(), reason="zh_core_web_md is not installed")
def test_spacy_does_not_label_phone_word_as_person() -> None:
    types = _types("電話是0912-345-678")
    assert "PHONE_NUMBER" in types
    assert "PERSON" not in types
    engine = build_analyzer_engine()
    hits = engine.analyze(text="身分證 A123456789", language="zh")
    id_hits = [hit for hit in hits if hit.entity_type == "TW_ID"]
    person_hits = [hit for hit in hits if hit.entity_type == "PERSON"]
    assert id_hits
    assert all("A123456789" not in "身分證 A123456789"[hit.start:hit.end] for hit in person_hits)
