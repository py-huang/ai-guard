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
