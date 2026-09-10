from __future__ import annotations

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
