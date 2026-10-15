"""Image-only credit-card and Taiwan ID cues from OCR boxes.

Presidio's text CreditCardRecognizer requires Luhn; RapidOCR often splits a PAN
into four groups. This module merges same-line boxes and treats card/ID layout
as sensitive without sending pixels to a cloud vision model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from safety_gateway.pii.checksum import TW_ID_PATTERN

_PAN_GROUPED = re.compile(
    r"(?<!\d)([2-6]\d{3})[\s\-]*(\d{4})[\s\-]*(\d{4})[\s\-]*(\d{3,4})(?!\d)"
)
_PAN_COMPACT = re.compile(r"(?<!\d)([2-6]\d{12,18})(?!\d)")
_TW_ID_SPACED = re.compile(
    r"(?<![A-Z0-9])([A-Z])[\s\-]*([1289])[\s\-]*(\d{2})[\s\-]*(\d{3})[\s\-]*(\d{3})(?![A-Z0-9])",
    re.IGNORECASE,
)
_CARD_HINTS = (
    "visa",
    "mastercard",
    "信用卡",
    "金融卡",
    "cardholder",
    "valid thru",
    "valid dates",
    "jcb",
    "銀聯",
)
_DIGIT_CONFUSIONS = str.maketrans({"O": "0", "I": "1", "L": "1", "S": "5", "B": "8", "Z": "2"})


@dataclass(frozen=True)
class SensitiveBox:
    left: int
    top: int
    width: int
    height: int
    entity_type: str


def detect_sensitive_boxes(
    boxes: list[dict[str, object]],
    *,
    pad: int = 6,
) -> tuple[list[SensitiveBox], set[str]]:
    """Return paint boxes and entity types from RapidOCR-style dict rows."""
    rows = _normalize_boxes(boxes)
    if not rows:
        return [], set()

    lines = _group_lines(rows)
    found: list[SensitiveBox] = []
    entities: set[str] = set()
    blob = " ".join(row["text"] for row in rows).lower()
    has_card_hint = any(hint in blob for hint in _CARD_HINTS)

    for line in lines:
        text = _line_text(line)
        compact = re.sub(r"[\s\-]", "", text)
        pan_boxes = _pan_boxes(line, text, compact, pad=pad)
        if pan_boxes:
            found.extend(pan_boxes)
            entities.add("CREDIT_CARD")
        elif has_card_hint and _looks_like_partial_pan(line):
            found.extend(_boxes_for_rows(line, "CREDIT_CARD", pad=pad))
            entities.add("CREDIT_CARD")

        id_boxes = _tw_id_boxes(line, text, compact, pad=pad)
        if id_boxes:
            found.extend(id_boxes)
            entities.add("TW_ID")

    return _unique_boxes(found), entities


def _normalize_boxes(boxes: list[dict[str, object]]) -> list[dict[str, int | str]]:
    rows: list[dict[str, int | str]] = []
    if not boxes:
        return rows
    # Support both list-of-dicts and the Presidio OCR payload shape.
    if boxes and "text" in boxes[0] and isinstance(boxes[0].get("text"), str):
        source = boxes
        for item in source:
            text = str(item.get("text") or "").strip()
            if not text:
                continue
            rows.append(
                {
                    "left": int(item.get("left") or 0),
                    "top": int(item.get("top") or 0),
                    "width": max(int(item.get("width") or 1), 1),
                    "height": max(int(item.get("height") or 1), 1),
                    "text": text,
                }
            )
        return rows
    return rows


def ocr_payload_to_boxes(payload: dict[str, list]) -> list[dict[str, object]]:
    texts = payload.get("text") or []
    boxes: list[dict[str, object]] = []
    for index, text in enumerate(texts):
        boxes.append(
            {
                "left": int(payload["left"][index]) if index < len(payload.get("left") or []) else 0,
                "top": int(payload["top"][index]) if index < len(payload.get("top") or []) else 0,
                "width": int(payload["width"][index]) if index < len(payload.get("width") or []) else 1,
                "height": int(payload["height"][index]) if index < len(payload.get("height") or []) else 1,
                "text": str(text or ""),
            }
        )
    return boxes


def _group_lines(rows: list[dict[str, int | str]]) -> list[list[dict[str, int | str]]]:
    ordered = sorted(rows, key=lambda row: (int(row["top"]), int(row["left"])))
    lines: list[list[dict[str, int | str]]] = []
    for row in ordered:
        placed = False
        for line in lines:
            anchor = line[0]
            tol = max(int(anchor["height"]), int(row["height"])) * 0.65
            if abs(int(row["top"]) - int(anchor["top"])) <= tol:
                line.append(row)
                placed = True
                break
        if not placed:
            lines.append([row])
    for line in lines:
        line.sort(key=lambda row: int(row["left"]))
    return lines


def _line_text(line: list[dict[str, int | str]]) -> str:
    return " ".join(str(row["text"]) for row in line)


def _pan_boxes(
    line: list[dict[str, int | str]],
    text: str,
    compact: str,
    *,
    pad: int,
) -> list[SensitiveBox]:
    if _PAN_GROUPED.search(text) or _PAN_GROUPED.search(compact) or _PAN_COMPACT.search(compact):
        return _boxes_for_rows([row for row in line if _has_digit(str(row["text"]))], "CREDIT_CARD", pad=pad)
    return []


def _looks_like_partial_pan(line: list[dict[str, int | str]]) -> bool:
    digit_groups = [re.sub(r"\D", "", str(row["text"])) for row in line]
    groups = [item for item in digit_groups if 3 <= len(item) <= 4]
    return len(groups) >= 3


def _tw_id_boxes(
    line: list[dict[str, int | str]],
    text: str,
    compact: str,
    *,
    pad: int,
) -> list[SensitiveBox]:
    candidates = _tw_id_candidates(text) + _tw_id_candidates(compact)
    for candidate in candidates:
        normalized = _normalize_tw_id(candidate)
        if not normalized:
            continue
        return _boxes_for_rows(line, "TW_ID", pad=pad)
    return []


def _tw_id_candidates(text: str) -> list[str]:
    found: list[str] = []
    for match in _TW_ID_SPACED.finditer(text.upper().translate(_DIGIT_CONFUSIONS)):
        found.append("".join(match.groups()))
    compact = re.sub(r"[\s\-]", "", text.upper().translate(_DIGIT_CONFUSIONS))
    for match in re.finditer(r"[A-Z][1289]\d{8}", compact):
        found.append(match.group(0))
    return found


def _normalize_tw_id(value: str) -> str | None:
    compact = re.sub(r"[\s\-]", "", value.upper().translate(_DIGIT_CONFUSIONS))
    if TW_ID_PATTERN.fullmatch(compact):
        return compact
    return None


def _has_digit(text: str) -> bool:
    return any(ch.isdigit() for ch in text)


def _boxes_for_rows(rows: list[dict[str, int | str]], entity_type: str, *, pad: int) -> list[SensitiveBox]:
    boxes: list[SensitiveBox] = []
    for row in rows:
        left = max(int(row["left"]) - pad, 0)
        top = max(int(row["top"]) - pad, 0)
        boxes.append(
            SensitiveBox(
                left=left,
                top=top,
                width=int(row["width"]) + pad * 2,
                height=int(row["height"]) + pad * 2,
                entity_type=entity_type,
            )
        )
    if len(rows) >= 2:
        left = min(int(row["left"]) for row in rows) - pad
        top = min(int(row["top"]) for row in rows) - pad
        right = max(int(row["left"]) + int(row["width"]) for row in rows) + pad
        bottom = max(int(row["top"]) + int(row["height"]) for row in rows) + pad
        boxes.append(
            SensitiveBox(
                left=max(left, 0),
                top=max(top, 0),
                width=max(right - max(left, 0), 1),
                height=max(bottom - max(top, 0), 1),
                entity_type=entity_type,
            )
        )
    return boxes


def _unique_boxes(boxes: list[SensitiveBox]) -> list[SensitiveBox]:
    seen: set[tuple[int, int, int, int, str]] = set()
    unique: list[SensitiveBox] = []
    for box in boxes:
        key = (box.left, box.top, box.width, box.height, box.entity_type)
        if key in seen:
            continue
        seen.add(key)
        unique.append(box)
    return unique
