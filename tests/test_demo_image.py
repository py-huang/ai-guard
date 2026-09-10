from __future__ import annotations

import io

from PIL import Image

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.demo_image import PII_LINES, render_contact_book, render_redacted_contact_book


def _black_ratio(png: bytes) -> float:
    with Image.open(io.BytesIO(png)) as image:
        rgb = image.convert("RGB")
        samples = [
            rgb.getpixel((x, y))
            for y in range(0, rgb.height, 8)
            for x in range(0, rgb.width, 8)
        ]
    return sum(1 for pixel in samples if pixel == (0, 0, 0)) / len(samples)


def test_demo_contact_book_redacts_known_boxes() -> None:
    original, redacted = render_redacted_contact_book()
    assert original.startswith(b"\x89PNG")
    assert redacted.startswith(b"\x89PNG")
    assert redacted != original
    assert _black_ratio(redacted) > _black_ratio(original)
    raw, boxes = render_contact_book()
    assert len(boxes) == len(PII_LINES)
    assert raw == original


def test_gateway_demo_contact_book() -> None:
    original, redacted = AISafetyGateway().demo_contact_book()
    assert len(redacted) > 100
    assert original != redacted
