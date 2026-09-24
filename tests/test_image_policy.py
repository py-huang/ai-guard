from __future__ import annotations

import io

from PIL import Image, ImageDraw

from safety_gateway.pii.image_policy import classify_image_share, redaction_coverage


def _png(width: int = 100, height: int = 100, color: tuple[int, int, int] = (240, 240, 240)) -> bytes:
    image = Image.new("RGB", (width, height), color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _paint_ratio(ratio: float) -> bytes:
    image = Image.new("RGB", (100, 100), color=(240, 240, 240))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 99, int(100 * ratio) - 1], fill=(0, 0, 0))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_coverage_blocks_when_most_pixels_change() -> None:
    original = _png()
    covered = _paint_ratio(0.9)
    assert redaction_coverage(original, covered) >= 0.8
    blocked, reason = classify_image_share(redaction_coverage(original, covered), [])
    assert blocked is True
    assert reason == "coverage"


def test_coverage_allows_small_redaction() -> None:
    original = _png()
    covered = _paint_ratio(0.2)
    blocked, reason = classify_image_share(redaction_coverage(original, covered), ["PERSON"])
    assert blocked is False
    assert reason is None


def test_id_document_is_high_sensitivity() -> None:
    blocked, reason = classify_image_share(0.1, ["PERSON", "TW_ID"])
    assert blocked is True
    assert reason == "sensitive"
