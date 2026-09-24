"""Shareability rules for a redacted child photo: coverage and high-sensitivity PII."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

COVERAGE_BLOCK_RATIO = 0.80
HIGH_SENSITIVITY_ENTITIES = frozenset(
    {
        "TW_ID",
        "TW_PASSPORT",
        "TW_DRIVER_LICENSE",
        "TW_BANK_ACCOUNT",
        "CREDIT_CARD",
        "IBAN_CODE",
        "US_BANK_NUMBER",
        "US_ITIN",
    }
)


def redaction_coverage(original: bytes, redacted: bytes) -> float:
    """Fraction of pixels that changed after redaction, 0.0–1.0."""
    if not original or not redacted:
        return 0.0
    with Image.open(io.BytesIO(original)) as first, Image.open(io.BytesIO(redacted)) as second:
        source = first.convert("RGB")
        masked = second.convert("RGB")
        if masked.size != source.size:
            masked = masked.resize(source.size)
        source_arr = np.asarray(source)
        masked_arr = np.asarray(masked)
    if source_arr.size == 0:
        return 0.0
    changed = np.any(source_arr != masked_arr, axis=2)
    return float(changed.mean())


def classify_image_share(coverage: float, entities: list[str] | set[str]) -> tuple[bool, str | None]:
    """Return (blocked, reason) for child image sharing.

    Current redaction can label OCR PII and faces. It does not classify
    body, violence, or voyeurism. Those stay in the child-facing why list
    as policy, not as a vision verdict.
    """
    kinds = {item.upper() for item in entities}
    if kinds & HIGH_SENSITIVITY_ENTITIES:
        return True, "sensitive"
    if coverage >= COVERAGE_BLOCK_RATIO:
        return True, "coverage"
    return False, None
