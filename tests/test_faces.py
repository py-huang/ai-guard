from __future__ import annotations

import io

from PIL import Image

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.demo_image import classmate_portrait_path, render_nametag_card
from safety_gateway.pii.faces import detect_faces_opencv
from safety_gateway.pii.image import InMemoryImageRedactor
from safety_gateway.pii.ocr import ocr_lines


class _PassthroughEngine:
    def redact(self, image: Image.Image, **_: object) -> Image.Image:
        return image.copy()


def test_injected_face_boxes_are_blacked_out() -> None:
    image = Image.new("RGB", (120, 120), color=(200, 180, 160))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    redactor = InMemoryImageRedactor(
        engine=_PassthroughEngine(),
        face_detector=lambda _image: [(20, 20, 80, 80)],
    )
    result = redactor.redact_image_in_memory(buffer.getvalue())
    with Image.open(io.BytesIO(result)) as redacted:
        assert redacted.getpixel((50, 50)) == (0, 0, 0)
        assert redacted.getpixel((2, 2)) != (0, 0, 0)


def test_nametag_card_hides_classmate_name() -> None:
    original = render_nametag_card()
    blob = "".join(ocr_lines(original))
    assert "林小華" in blob
    redacted = AISafetyGateway().redact_image_in_memory(original)
    remaining = "".join(ocr_lines(redacted))
    assert "林小華" not in remaining, remaining
    assert "中山國小" not in remaining, remaining


def test_classmate_portrait_redacts_face_and_name() -> None:
    path = classmate_portrait_path()
    assert path is not None
    original = path.read_bytes()
    with Image.open(io.BytesIO(original)) as image:
        faces = detect_faces_opencv(image.convert("RGB"))
    assert faces, "Haar should see the portrait face"
    left, top, right, bottom = faces[0]
    redacted = AISafetyGateway().redact_image_in_memory(original)
    remaining = "".join(ocr_lines(redacted))
    assert "林小華" not in remaining, remaining
    with Image.open(io.BytesIO(redacted)) as image:
        cx = (left + right) // 2
        cy = (top + bottom) // 2
        assert image.getpixel((cx, cy)) == (0, 0, 0)
