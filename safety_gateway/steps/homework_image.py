"""Image generation routing: generate unless the request is a person / PII likeness."""

from __future__ import annotations

import io
import re

from PIL import Image, ImageDraw

IMAGE_GEN_INTENT: tuple[str, ...] = (
    "幫我畫",
    "請畫",
    "畫一張",
    "畫一個",
    "畫一朵",
    "畫給我",
    "畫出來給我",
    "生成一張",
    "生成一張圖",
    "生成圖片",
    "產生一張",
    "產生圖片",
    "幫我產生",
    "做一張圖",
    "的圖片",
    "生圖",
)

# Extra refuse when inbound content-safety did not already block.
# Short tokens like 「人」are omitted so 天氣 / 植物 still generate.
IMAGE_GEN_DENY: tuple[str, ...] = (
    "小朋友",
    "小孩",
    "同學",
    "人像",
    "的臉",
    "一個人",
    "真人",
    "自畫像",
    "證件照",
    "身分證",
    "護照",
    "信用卡",
)

REFUSE_MESSAGE = (
    "這種圖不適合在這裡畫。我們不能畫真人、同學、臉或證件。"
    "想看天氣、植物、形狀或故事場景，可以再說一次。"
)

GENERATE_CAPTION = "這是幫你畫的圖。如果想改成晴天、下雨或別的主題，再說一次就好。"

_TOKEN = re.compile(r"<[A-Z][A-Z0-9_]*_[1-9]\d*>")


def wants_image_generation(text: str) -> bool:
    haystack = (text or "").casefold()
    return any(cue.casefold() in haystack for cue in IMAGE_GEN_INTENT)


def is_denied_subject(text: str) -> bool:
    haystack = text or ""
    return any(topic in haystack for topic in IMAGE_GEN_DENY)


def image_gen_action(text: str) -> str:
    """Return generate, refuse, or chat."""
    if not wants_image_generation(text):
        return "chat"
    if is_denied_subject(text):
        return "refuse"
    return "generate"


def imagen_prompt(processed_text: str) -> str:
    cleaned = _TOKEN.sub(" ", processed_text or "").strip()
    return (
        "Child-safe illustration, simple friendly style for elementary school. "
        "No people, no faces, no photorealistic humans, no ID cards, no violence, no logos. "
        "If the subject is weather, draw a generic outdoor weather scene "
        "(sun, clouds, or rain) without a real address. "
        f"Subject requested: {cleaned[:400]}"
    )


def render_echo_homework_png() -> bytes:
    """Deterministic sun/cloud diagram so the playground works without the image model."""
    image = Image.new("RGB", (320, 320), color=(186, 220, 247))
    draw = ImageDraw.Draw(image)
    draw.ellipse((40, 40, 130, 130), fill=(255, 204, 64), outline=(232, 168, 24), width=3)
    draw.ellipse((140, 150, 230, 210), fill=(255, 255, 255), outline=(220, 228, 236), width=2)
    draw.ellipse((190, 140, 280, 210), fill=(255, 255, 255), outline=(220, 228, 236), width=2)
    draw.ellipse((170, 175, 250, 235), fill=(255, 255, 255))
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()
