"""Shareability rules for a redacted child photo: forbid categories then coverage."""

from __future__ import annotations

import io

import numpy as np
from PIL import Image

from safety_gateway.pii.image_forbid import classify_forbidden_image

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
        "IMAGE_DOCUMENT",
        "IMAGE_BODY",
        "IMAGE_VIOLENCE",
        "IMAGE_VOYEUR",
        "IMAGE_OTHER",
        "FACE",
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


def classify_image_share(
    coverage: float,
    entities: list[str] | set[str],
    ocr_text: str = "",
) -> tuple[bool, str | None]:
    """Return (blocked, reason) for child image sharing.

    Reasons align with the child why-list: body, violence, voyeur, document, other.
    Coverage remains a last-resort block when most pixels were already painted.
    """
    forbid = classify_forbidden_image(ocr_text, entities)
    if forbid:
        return True, forbid
    kinds = {item.upper() for item in entities}
    if "FACE" in kinds:
        return True, "face"
    if kinds & HIGH_SENSITIVITY_ENTITIES:
        return True, "document"
    if coverage >= COVERAGE_BLOCK_RATIO:
        return True, "coverage"
    return False, None
