from __future__ import annotations

import pytest

from safety_gateway.pii.analyzer import build_analyzer_engine
from safety_gateway.pii.checksum import generate_test_tw_national_id, is_valid_tw_national_id


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("A123456789", True),
        ("A123456780", False),
        ("B123456789", False),
        ("a123456789", True),
        ("A323456789", False),
        ("A023456789", False),
        ("1234567890", False),
        ("A12345678", False),
    ],
)
def test_tw_national_id_checksum(value: str, expected: bool) -> None:
    assert is_valid_tw_national_id(value) is expected


def test_generated_ids_are_detected_without_a_name_list() -> None:
    engine = build_analyzer_engine()
    for letter, body in (("A", "2345678"), ("B", "1111111"), ("H", "8765432")):
        value = generate_test_tw_national_id(letter, "1", body)
        assert is_valid_tw_national_id(value)
        text = f"聯絡資料 {value}"
        spans = {text[hit.start : hit.end] for hit in engine.analyze(text=text, language="zh") if hit.entity_type == "TW_ID"}
        assert value in spans
