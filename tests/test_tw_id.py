from __future__ import annotations

import pytest

from safety_gateway.pii.checksum import is_valid_tw_national_id


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
