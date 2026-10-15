"""Optional Gemini vision fallback when OCR cannot see body/violence/voyeur/ads.

Local OCR/layout still runs first. Vision is skipped unless IMAGE_FORBID_VISION
is auto/1 and GEMINI_API_KEY exists. Tests set IMAGE_FORBID_VISION=0.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
from pathlib import Path

from PIL import Image

_ALLOWED = {"body", "violence", "voyeur", "document", "other"}
_PROMPT = """You help a Taiwan elementary-school safety filter.
Classify the photo. Reply JSON only: {"category":"<one>"}
Categories:
- body: any unclothed human body, including oil nudes AND museum marble/bronze nude statues
- violence: combat or war. Include distant troop lines, cannons, cavalry, manuscript/miniature battle scenes, night-vision soldiers with rifles, wounded people, gore. Small figures still count if the scene is a battlefield.
- voyeur: ONLY when the MAIN subject is a hidden camera, CCTV dome, door peephole, webcam, or spy-camera gadget. Night-vision soldiers are violence, not voyeur. Paper spy-case documents are document, not voyeur.
- document: any ID, license, passport, bank/insurance card — including blurry/old foreign papers, Hebrew/Arabic forms, Taiwan 健保卡/國民身分證/居留證/自然人憑證/戶口名簿/駕照/護照
- other: tobacco, alcohol, gambling, casino, betel-nut, lottery ads
- safe: landscapes, maps, village photos, ordinary buildings, school work, clothed portraits without weapons
If unsure between safe and violence for a historical battle painting, choose violence.
"""


def vision_enabled() -> bool:
    flag = os.environ.get("IMAGE_FORBID_VISION", "auto").strip().lower()
    if flag in {"0", "false", "off", "no"}:
        return False
    if flag in {"1", "true", "on", "yes", "auto", ""}:
        return bool(_api_key())
    return False


def classify_image_pixels(image_bytes: bytes) -> str | None:
    if not vision_enabled() or not image_bytes:
        return None
    cached = _cache_read(image_bytes)
    if cached in _ALLOWED or cached == "safe":
        return None if cached == "safe" else cached
    try:
        category = _gemini_classify(_thumbnail(image_bytes))
    except Exception:
        return None
    if category:
        _cache_write(image_bytes, category)
    if category in _ALLOWED:
        return category
    return None


def _api_key() -> str | None:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _thumbnail(image_bytes: bytes) -> bytes:
    with Image.open(io.BytesIO(image_bytes)) as opened:
        image = opened.convert("RGB")
        image.thumbnail((512, 512))
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=70)
        return buffer.getvalue()


def _gemini_classify(jpeg: bytes) -> str | None:
    from google import genai
    from google.genai import types

    model = os.environ.get("GEMINI_MODEL", "").strip() or "gemini-2.5-flash"
    client = genai.Client(api_key=_api_key())
    # BLOCK_NONE so nudes/gore still return a label instead of an empty safety block.
    off = [
        types.SafetySetting(category=item, threshold="BLOCK_NONE")
        for item in (
            "HARM_CATEGORY_HARASSMENT",
            "HARM_CATEGORY_HATE_SPEECH",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "HARM_CATEGORY_DANGEROUS_CONTENT",
        )
    ]
    response = client.models.generate_content(
        model=model,
        contents=[
            types.Content(
                role="user",
                parts=[
                    types.Part(text=_PROMPT),
                    types.Part.from_bytes(data=jpeg, mime_type="image/jpeg"),
                ],
            )
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            safety_settings=off,
        ),
    )
    text = (response.text or "").strip()
    if not text:
        return None
    match = re.search(r"\{.*\}", text, re.DOTALL)
    payload = json.loads(match.group(0) if match else text)
    category = str(payload.get("category") or "").strip().lower()
    if category in _ALLOWED or category == "safe":
        return category
    return None


def _cache_dir() -> Path:
    return Path(os.environ.get("IMAGE_FORBID_CACHE", "") or Path.cwd() / ".vision-cache")


def _digest(image_bytes: bytes) -> str:
    return hashlib.sha256(image_bytes).hexdigest()


def _cache_read(image_bytes: bytes) -> str | None:
    path = _cache_dir() / f"{_digest(image_bytes)}.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip() or None
    return None


def _cache_write(image_bytes: bytes, category: str) -> None:
    folder = _cache_dir()
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{_digest(image_bytes)}.txt").write_text(category, encoding="utf-8")
