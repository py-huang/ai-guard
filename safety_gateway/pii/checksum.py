"""Taiwan National ID (身分證字號) checksum: alphabet mapping + weighted modulo 10."""

from __future__ import annotations

import re

# Official letter-to-region numeric mapping used by the checksum (I=34, O=35, W=32, Z=33).
TW_ID_LETTER_CODES: dict[str, int] = {
    "A": 10,
    "B": 11,
    "C": 12,
    "D": 13,
    "E": 14,
    "F": 15,
    "G": 16,
    "H": 17,
    "I": 34,
    "J": 18,
    "K": 19,
    "L": 20,
    "M": 21,
    "N": 22,
    "O": 35,
    "P": 23,
    "Q": 24,
    "R": 25,
    "S": 26,
    "T": 27,
    "U": 28,
    "V": 29,
    "W": 32,
    "X": 30,
    "Y": 31,
    "Z": 33,
}

# Weights for the 11 digits produced after expanding the leading letter.
TW_ID_WEIGHTS: tuple[int, ...] = (1, 9, 8, 7, 6, 5, 4, 3, 2, 1, 1)

TW_ID_PATTERN = re.compile(r"^[A-Z][1289]\d{8}$")


def is_valid_tw_national_id(value: str) -> bool:
    """Return True iff `value` matches `[A-Z][1289]\\d{8}` and passes modulo-10 checksum."""
    candidate = value.strip().upper()
    if TW_ID_PATTERN.fullmatch(candidate) is None:
        return False
    region = TW_ID_LETTER_CODES[candidate[0]]
    digits = (region // 10, region % 10, *(int(ch) for ch in candidate[1:]))
    weighted = sum(digit * weight for digit, weight in zip(digits, TW_ID_WEIGHTS, strict=True))
    return weighted % 10 == 0
