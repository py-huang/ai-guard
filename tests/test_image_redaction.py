from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageDraw

from safety_gateway.pii.image import InMemoryImageRedactor


class _FakeEngine:
    def redact(self, image: Image.Image, fill: tuple[int, int, int] = (0, 0, 0), **_: Any) -> Image.Image:
        redacted = image.copy()
        draw = ImageDraw.Draw(redacted)
        draw.rectangle([0, 0, 40, 20], fill=fill)
        return redacted


def _png_bytes() -> bytes:
    image = Image.new("RGB", (80, 40), color=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_redact_image_in_memory_returns_png_without_disk(tmp_path) -> None:  # type: ignore[no-untyped-def]
    before_files = set(tmp_path.iterdir())
    redactor = InMemoryImageRedactor(engine=_FakeEngine())
    result = redactor.redact_image_in_memory(_png_bytes())
    after_files = set(tmp_path.iterdir())

    assert result.startswith(b"\x89PNG")
    assert result != _png_bytes()
    assert after_files == before_files
    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "PNG"
        assert image.getpixel((1, 1)) == (0, 0, 0)
