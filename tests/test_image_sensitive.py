from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.checksum import is_valid_tw_national_id
from safety_gateway.pii.image_sensitive import detect_sensitive_boxes

pytest.importorskip("rapidocr_onnxruntime")

_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "sensitive_images"


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def render_credit_card(pan: str, *, dark: bool, brand: str) -> bytes:
    background = (18, 48, 92) if dark else (236, 242, 248)
    foreground = (255, 255, 255) if dark else (20, 24, 32)
    image = Image.new("RGB", (1012, 638), background)
    draw = ImageDraw.Draw(image)
    draw.text((48, 48), brand, fill=foreground, font=_font(36))
    draw.text((48, 280), pan, fill=foreground, font=_font(52))
    draw.text((48, 380), "CARDHOLDER NAME", fill=foreground, font=_font(28))
    draw.text((48, 500), "VISA  VALID THRU 12/28", fill=foreground, font=_font(28))
    return _png(image)


def render_taiwan_id_back() -> bytes:
    image = Image.new("RGB", (1012, 638), (248, 244, 232))
    draw = ImageDraw.Draw(image)
    draw.rectangle([24, 24, 988, 614], outline=(40, 40, 40), width=4)
    draw.text((48, 48), "父  範例父親", fill=(20, 24, 32), font=_font(32))
    draw.text((420, 48), "母  範例母親", fill=(20, 24, 32), font=_font(32))
    draw.text((48, 140), "配偶  範例配偶", fill=(20, 24, 32), font=_font(32))
    draw.text((48, 220), "役別  /", fill=(20, 24, 32), font=_font(32))
    draw.text((48, 300), "出生地  臺北市", fill=(20, 24, 32), font=_font(32))
    draw.text((48, 380), "住址  臺北市內湖區葫洲里1鄰", fill=(20, 24, 32), font=_font(32))
    draw.text((48, 460), "民權東路六段1號", fill=(20, 24, 32), font=_font(32))
    return _png(image)


def render_postal_passbook() -> bytes:
    image = Image.new("RGB", (1012, 638), (198, 214, 92))
    draw = ImageDraw.Draw(image)
    draw.text((48, 36), "郵政存簿儲金簿", fill=(20, 24, 32), font=_font(40))
    draw.text((48, 140), "局號  700", fill=(20, 24, 32), font=_font(32))
    draw.text((48, 220), "帳號  0311248  0287828", fill=(20, 24, 32), font=_font(32))
    draw.text((48, 300), "戶名  範例戶名", fill=(20, 24, 32), font=_font(32))
    draw.text((48, 380), "郵局  板橋三民路郵局", fill=(20, 24, 32), font=_font(32))
    draw.text((48, 460), "電話:02-29518120", fill=(20, 24, 32), font=_font(28))
    return _png(image)


def render_taiwan_id(national_id: str, *, name: str = "測試兒童") -> bytes:
    image = Image.new("RGB", (1012, 638), (248, 244, 232))
    draw = ImageDraw.Draw(image)
    draw.rectangle([24, 24, 988, 614], outline=(160, 40, 40), width=6)
    draw.text((48, 48), "中華民國國民身分證", fill=(120, 24, 24), font=_font(40))
    draw.text((48, 160), f"姓名  {name}", fill=(20, 24, 32), font=_font(36))
    draw.text((48, 260), f"身分證字號  {national_id}", fill=(20, 24, 32), font=_font(40))
    draw.text((48, 360), "出生  民國 102 年 3 月 2 日", fill=(20, 24, 32), font=_font(32))
    return _png(image)


def _cases() -> list[tuple[str, bytes, str, str]]:
    assert is_valid_tw_national_id("A123456789")
    return [
        ("card_fubon_demo", render_credit_card("5241 0856 8888 8888", dark=True, brand="TAIPEI FUBON BANK"), "CREDIT_CARD", "5241085688888888"),
        ("card_union_demo", render_credit_card("4514 4500 1234 5678", dark=True, brand="UNION BANK OF TAIWAN"), "CREDIT_CARD", "4514450012345678"),
        ("card_visa_test", render_credit_card("4111 1111 1111 1111", dark=False, brand="VISA TEST"), "CREDIT_CARD", "4111111111111111"),
        ("card_mastercard", render_credit_card("5555 5555 5555 4444", dark=True, brand="MASTERCARD"), "CREDIT_CARD", "5555555555554444"),
        ("card_dashed", render_credit_card("4000-0000-0000-0002", dark=False, brand="CREDIT CARD"), "CREDIT_CARD", "4000000000000002"),
        ("card_compact", render_credit_card("4012888888881881", dark=True, brand="VISA"), "CREDIT_CARD", "4012888888881881"),
        ("id_standard", render_taiwan_id("A123456789"), "TW_ID", "A123456789"),
        ("id_spaced", render_taiwan_id("A12 345 6789"), "TW_ID", "A123456789"),
        ("id_format_only", render_taiwan_id("A111111111"), "TW_ID", "A111111111"),
        ("id_second_valid", render_taiwan_id("A123456789", name="範例姓名"), "TW_ID", "A123456789"),
        ("id_back_layout", render_taiwan_id_back(), "TW_ID", "範例父親"),
        ("postal_passbook", render_postal_passbook(), "IMAGE_DOCUMENT", "0311248"),
    ]


def test_grouped_ocr_boxes_detect_demo_pans_without_luhn() -> None:
    boxes = [
        {"left": 10, "top": 40, "width": 80, "height": 24, "text": "5241"},
        {"left": 100, "top": 42, "width": 80, "height": 24, "text": "0856"},
        {"left": 190, "top": 41, "width": 80, "height": 24, "text": "8888"},
        {"left": 280, "top": 40, "width": 80, "height": 24, "text": "8888"},
    ]
    painted, entities = detect_sensitive_boxes(boxes)
    assert "CREDIT_CARD" in entities
    assert painted


@pytest.mark.parametrize("name,png,entity,secret", _cases(), ids=[item[0] for item in _cases()])
def test_ten_sensitive_images_are_blocked_and_masked(name: str, png: bytes, entity: str, secret: str) -> None:
    _FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    (_FIXTURE_DIR / f"{name}.png").write_bytes(png)
    result = AISafetyGateway().redact_image("image-sensitive", png)
    assert entity in result.detected_entities, (name, result.detected_entities)
    assert result.blocked is True
    assert result.block_reason == "document"
    remaining = "".join(
        __import__("safety_gateway.pii.ocr", fromlist=["ocr_lines"]).ocr_lines(result.image_bytes)
    ).replace(" ", "").replace("-", "")
    compact = secret.replace(" ", "").replace("-", "")
    assert compact not in remaining, (name, remaining)
