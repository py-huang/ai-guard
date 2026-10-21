from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageDraw

from safety_gateway.pii.image import InMemoryImageRedactor, keep_image_person_span, _line_holds_person_name, _too_large_for_person
from safety_gateway.pii.image_sensitive import SensitiveBox


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
    redactor = InMemoryImageRedactor(engine=_FakeEngine(), face_detector=lambda _image: [])
    result = redactor.redact_image_in_memory(_png_bytes())
    after_files = set(tmp_path.iterdir())

    assert result.startswith(b"\x89PNG")
    assert result != _png_bytes()
    assert after_files == before_files
    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "PNG"
        assert image.getpixel((1, 1)) == (0, 0, 0)


def test_redact_with_entities_reports_faces() -> None:
    redactor = InMemoryImageRedactor(
        engine=_FakeEngine(),
        face_detector=lambda _image: [(1, 1, 10, 10)],
    )
    png, entities = redactor.redact_image_with_entities(_png_bytes())
    assert png.startswith(b"\x89PNG")
    assert entities == ["FACE"]


def test_form_labels_are_not_image_person_names() -> None:
    assert keep_image_person_span("PAMIWAN") is False
    assert keep_image_person_span("THAO") is False
    assert keep_image_person_span("Taiwanese") is False
    assert keep_image_person_span("Race/Ethnicity") is False
    assert keep_image_person_span("王小明") is True
    assert keep_image_person_span("Jane Doe") is True
    assert keep_image_person_span("陳銘") is True
    assert _line_holds_person_name("家長簽名 陳銘") is True
    column = SensitiveBox(left=200, top=0, width=40, height=400, entity_type="PERSON")
    assert _too_large_for_person(column, 400, 500) is True
    signature = SensitiveBox(left=40, top=420, width=50, height=24, entity_type="PERSON")
    assert _too_large_for_person(signature, 400, 500) is False
