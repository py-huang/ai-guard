"""Annotate Traditional Chinese with Zhuyin (Bopomofo) for child-facing replies.

Display follows cmex-30/Bopomofo_on_Web: HTML ruby + BopomofoRuby OpenType font.
That project does not convert 漢字 → 注音, so readings still come from pypinyin
Style.BOPOMOFO. Neutral ˙ is prefixed; ˊ ˇ ˋ are suffixed. Not innerHTML of LLM text.
"""

from __future__ import annotations

import re

from pypinyin import Style, pinyin

from safety_gateway.schemas import StrictModel

_TOKEN = re.compile(r"<[A-Z][A-Z0-9_]*_[1-9]\d*>")
_HAN = re.compile(r"[\u3400-\u9fff]+")


_TONE_MARKS = ("˙", "ˊ", "ˇ", "ˋ")


class ZhuyinPart(StrictModel):
    text: str
    zhuyin: str | None = None
    letters: str | None = None
    tone: str | None = None


def to_zhuyin_parts(text: str) -> list[ZhuyinPart]:
    source = text or ""
    parts: list[ZhuyinPart] = []
    cursor = 0
    for match in _TOKEN.finditer(source):
        if match.start() > cursor:
            parts.extend(_annotate_span(source[cursor : match.start()]))
        parts.append(ZhuyinPart(text=match.group(0), zhuyin=None))
        cursor = match.end()
    if cursor < len(source):
        parts.extend(_annotate_span(source[cursor:]))
    return parts or [ZhuyinPart(text=source, zhuyin=None)]


def _annotate_span(span: str) -> list[ZhuyinPart]:
    parts: list[ZhuyinPart] = []
    cursor = 0
    for match in _HAN.finditer(span):
        if match.start() > cursor:
            parts.append(ZhuyinPart(text=span[cursor : match.start()], zhuyin=None))
        parts.extend(_annotate_hanzi(match.group(0)))
        cursor = match.end()
    if cursor < len(span):
        parts.append(ZhuyinPart(text=span[cursor:], zhuyin=None))
    return parts


def _annotate_hanzi(chunk: str) -> list[ZhuyinPart]:
    readings = pinyin(chunk, style=Style.BOPOMOFO, strict=False)
    chars = list(chunk)
    if len(readings) != len(chars):
        readings = [item for ch in chars for item in pinyin(ch, style=Style.BOPOMOFO, strict=False)]
    parts: list[ZhuyinPart] = []
    for char, reading in zip(chars, readings):
        raw = (reading[0] if reading else "") or ""
        letters, tone = _split_bopomofo(raw)
        full = _join_bopomofo(letters, tone)
        parts.append(
            ZhuyinPart(
                text=char,
                zhuyin=full or None,
                letters=letters or None,
                tone=tone,
            )
        )
    return parts


def _split_bopomofo(value: str) -> tuple[str, str | None]:
    """Split letters from tone. Neutral ˙ sits above the reading; other tones stay beside."""
    cleaned = (value or "").strip()
    tone = next((mark for mark in _TONE_MARKS if mark in cleaned), None)
    letters = cleaned
    for mark in _TONE_MARKS:
        letters = letters.replace(mark, "")
    return letters.strip(), tone


def _join_bopomofo(letters: str, tone: str | None) -> str:
    if not letters and not tone:
        return ""
    if tone == "˙":
        return f"˙{letters}"
    return f"{letters}{tone or ''}"


def _normalize_bopomofo(value: str) -> str:
    letters, tone = _split_bopomofo(value)
    return _join_bopomofo(letters, tone)
