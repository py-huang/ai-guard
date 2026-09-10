"""Deterministic contact-book PNG with recorded PII boxes (no OCR required)."""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PII_LINES = (
    ("姓名", "王小明"),
    ("學校", "中山國小"),
    ("電話", "0912-345-678"),
    ("身分證字號", "A123456789"),
    ("住址", "台北市中正區重慶南路一段122號"),
)

_FONT_CANDIDATES = (
    "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/Supplemental/Songti.ttc",
    "/Library/Fonts/Arial Unicode.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
)


def render_contact_book(width: int = 900, height: int = 560) -> tuple[bytes, list[tuple[int, int, int, int]]]:
    """Draw a Taiwan 聯絡簿 page and return PNG bytes plus PII bounding boxes."""
    image = Image.new("RGB", (width, height), color=(252, 248, 239))
    draw = ImageDraw.Draw(image)
    title_font = _load_font(40)
    label_font = _load_font(28)
    draw.rectangle([0, 0, width, 86], fill=(47, 93, 74))
    draw.text((36, 22), "聯絡簿", font=title_font, fill=(255, 255, 255))
    boxes: list[tuple[int, int, int, int]] = []
    y = 120
    for label, value in PII_LINES:
        draw.text((40, y), f"{label}：", font=label_font, fill=(87, 83, 78))
        value_x = 220
        bbox = draw.textbbox((value_x, y), value, font=label_font)
        padded = (bbox[0] - 6, bbox[1] - 4, bbox[2] + 6, bbox[3] + 4)
        draw.text((value_x, y), value, font=label_font, fill=(28, 25, 23))
        boxes.append(padded)
        y += 72
    output = io.BytesIO()
    image.save(output, format="PNG")
    return output.getvalue(), boxes


def redact_boxes(image_bytes: bytes, boxes: list[tuple[int, int, int, int]]) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as opened:
        working = opened.convert("RGB")
        draw = ImageDraw.Draw(working)
        for box in boxes:
            draw.rectangle(box, fill=(0, 0, 0))
        output = io.BytesIO()
        working.save(output, format="PNG")
        return output.getvalue()


def render_redacted_contact_book() -> tuple[bytes, bytes]:
    original, boxes = render_contact_book()
    return original, redact_boxes(original, boxes)


def generated_fixture_path() -> Path | None:
    path = Path(__file__).resolve().parents[1] / "playground" / "static" / "taiwan-contact-book-pii.png"
    return path if path.is_file() else None


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for candidate in _FONT_CANDIDATES:
        path = Path(candidate)
        if not path.is_file():
            continue
        try:
            return ImageFont.truetype(str(path), size=size)
        except OSError:
            continue
    return ImageFont.load_default()
