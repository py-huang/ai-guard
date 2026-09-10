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
