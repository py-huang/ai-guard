"""Zero-disk image PII redaction via in-memory buffers only."""

from __future__ import annotations

import io
import re
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from PIL import Image

from safety_gateway.pii.faces import FaceBox, detect_faces_opencv, redact_face_boxes
from safety_gateway.pii.image_forbid import extra_forbid_entities
from safety_gateway.pii.image_sensitive import SensitiveBox, detect_sensitive_boxes, ocr_payload_to_boxes
from safety_gateway.pii.ocr import ImageOcrUnavailable, build_ocr, isolate_runtime_caches, ocr_payload
from safety_gateway.pii.taiwan_names import is_plausible_tw_name

if TYPE_CHECKING:
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer
    from presidio_image_redactor import ImageRedactorEngine


PNG_CONTENT_TYPE = "image/png"
_BLACK_FILL = (0, 0, 0)
_PAINT_ENTITY_TYPES = frozenset(
    {
        "PERSON",
        "SCHOOL",
        "PHONE_NUMBER",
        "LOCATION",
        "EMAIL_ADDRESS",
        "EMAIL",
        "TW_ID",
        "SCHOOL_CLASS",
        "STUDENT_ID",
        "IG_HANDLE",
        "TW_PASSPORT",
        "TW_DRIVER_LICENSE",
        "TW_BANK_ACCOUNT",
        "CREDIT_CARD",
    }
)
_LATIN_PERSON = re.compile(r"^[A-Z][a-z]{1,20}(?:[ \-][A-Z][a-z]{1,20})+$")

__all__ = ["ImageOcrUnavailable", "InMemoryImageRedactor"]


class InMemoryImageRedactor:
    """Redact faces, then OCR text PII, without writing the source image to disk.

    Presidio Image Redactor identifies written PII. Classmate faces are a separate
    OpenCV pass because Presidio does not detect faces.
    """

    def __init__(
        self,
        engine: ImageRedactorEngine | None = None,
        analyzer_engine: AnalyzerEngine | None = None,
        ad_hoc_recognizers: list[PatternRecognizer] | None = None,
        face_detector: Callable[[Image.Image], Sequence[FaceBox]] | None = None,
        redact_faces: bool = True,
    ) -> None:
        isolate_runtime_caches()
        self._engine = engine
        self._analyzer_engine = analyzer_engine
        self._ad_hoc_recognizers = ad_hoc_recognizers
        self._face_detector = face_detector or detect_faces_opencv
        self._redact_faces = redact_faces
        self._ocr_name = "injected" if engine is not None else "rapidocr"

    def redact_image_in_memory(self, image_bytes: bytes) -> bytes:
        redacted, _entities = self.redact_image_with_entities(image_bytes)
        return redacted

    def redact_image_with_entities(self, image_bytes: bytes) -> tuple[bytes, list[str]]:
        if not image_bytes:
            raise ValueError("image_bytes must be a non-empty byte buffer")

        with Image.open(io.BytesIO(image_bytes)) as opened:
            opened.load()
            working = opened.convert("RGB")

        entities, extra_boxes = self._detected_entities(image_bytes, working)
        if self._redact_faces:
            working = redact_face_boxes(working, self._face_detector(working))

        # Injected engines (tests) still paint themselves. Production RapidOCR
        # boxes from Presidio are often a whole table column — we paint curated boxes only.
        if self._engine is not None:
            try:
                redacted = self._engine.redact(
                    working,
                    fill=_BLACK_FILL,
                    ad_hoc_recognizers=self._ad_hoc_recognizers,
                    language="zh",
                )
            except ImageOcrUnavailable:
                raise
            except Exception as exc:
                blob = str(exc).lower()
                if "tesseract" in blob:
                    raise ImageOcrUnavailable(
                        "系統 Tesseract 不可用。這個專案改在虛擬環境用 RapidOCR，"
                        "請確認 .venv 已安裝 rapidocr-onnxruntime。"
                    ) from exc
                raise
        else:
            redacted = working

        if extra_boxes:
            from PIL import ImageDraw

            draw = ImageDraw.Draw(redacted)
            width, height = redacted.size
            for box in extra_boxes:
                left, top, right, bottom = _visible_rect(box, width, height)
                draw.rectangle([left, top, right, bottom], fill=_BLACK_FILL)
        if {"TW_ID", "CREDIT_CARD", "IMAGE_DOCUMENT", "IMAGE_BODY", "IMAGE_VIOLENCE", "IMAGE_VOYEUR", "IMAGE_OTHER", "FACE"} & set(entities):
            from PIL import ImageDraw

            draw = ImageDraw.Draw(redacted)
            draw.rectangle([0, 0, redacted.size[0], redacted.size[1]], fill=_BLACK_FILL)

        output = io.BytesIO()
        redacted.save(output, format="PNG", optimize=True)
        return output.getvalue(), entities

    def _detected_entities(self, image_bytes: bytes, working: Image.Image) -> tuple[list[str], list]:
        found: set[str] = set()
        extra_boxes: list = []
        if self._redact_faces and self._face_detector(working):
            found.add("FACE")
        payload: dict[str, list] | None = None
        try:
            payload = ocr_payload(image_bytes)
        except Exception:
            payload = None
        if payload:
            extra_boxes, layout_entities = detect_sensitive_boxes(ocr_payload_to_boxes(payload))
            found.update(layout_entities)
            text = "\n".join(str(item) for item in payload.get("text") or [] if str(item).strip())
            found.update(extra_forbid_entities(text, image_bytes))
            image_size = working.size
            if text and self._analyzer_engine is not None:
                hits = self._analyzer_engine.analyze(text=text, language="zh")
                paint_hits = [hit for hit in hits if _keep_image_hit(text, hit)]
                extra_boxes.extend(_boxes_for_text_hits(payload, paint_hits, image_size))
            extra_boxes.extend(_person_boxes_from_ocr_lines(payload, image_size))
            found.update(box.entity_type for box in extra_boxes)
        return sorted(found), extra_boxes

    def _engine_instance(self) -> ImageRedactorEngine:
        if self._engine is not None:
            return self._engine
        from presidio_image_redactor import ImageAnalyzerEngine, ImageRedactorEngine

        ocr = build_ocr()
        self._ocr_name = getattr(ocr, "name", type(ocr).__name__)
        image_analyzer = ImageAnalyzerEngine(
            analyzer_engine=self._analyzer_engine,
            ocr=ocr,
        )
        self._engine = ImageRedactorEngine(image_analyzer_engine=image_analyzer)
        return self._engine


def keep_image_person_span(span: str) -> bool:
    compact = "".join(ch for ch in span if "\u4e00" <= ch <= "\u9fff")
    if compact and is_plausible_tw_name(compact):
        return True
    return bool(_LATIN_PERSON.fullmatch(span.strip()))


def _keep_image_hit(text: str, hit: object) -> bool:
    entity = getattr(hit, "entity_type", None)
    if entity not in _PAINT_ENTITY_TYPES:
        return False
    start = int(getattr(hit, "start", 0))
    end = int(getattr(hit, "end", 0))
    span = text[start:end]
    if entity == "PERSON":
        return keep_image_person_span(span)
    return bool(span.strip())


def _ocr_rows(payload: dict[str, list]) -> list[tuple[str, SensitiveBox]]:
    texts = [str(item) for item in payload.get("text") or []]
    lefts = payload.get("left") or []
    tops = payload.get("top") or []
    widths = payload.get("width") or []
    heights = payload.get("height") or []
    rows: list[tuple[str, SensitiveBox]] = []
    for index, line in enumerate(texts):
        if index >= len(lefts):
            break
        rows.append(
            (
                line,
                SensitiveBox(
                    left=int(lefts[index]),
                    top=int(tops[index]),
                    width=max(int(widths[index]), 1),
                    height=max(int(heights[index]), 1),
                    entity_type="PERSON",
                ),
            )
        )
    return rows


def _too_large_for_person(box: SensitiveBox, image_width: int, image_height: int) -> bool:
    if image_width < 1 or image_height < 1:
        return True
    if box.height > image_height * 0.18:
        return True
    if box.width > image_width * 0.45:
        return True
    return (box.width * box.height) > (image_width * image_height * 0.08)


def _person_boxes_from_ocr_lines(payload: dict[str, list], image_size: tuple[int, int]) -> list[SensitiveBox]:
    image_width, image_height = image_size
    found: list[SensitiveBox] = []
    for line, box in _ocr_rows(payload):
        if not _line_holds_person_name(line):
            continue
        if _too_large_for_person(box, image_width, image_height):
            continue
        found.append(box)
    return found


def _line_holds_person_name(line: str) -> bool:
    chars = "".join(ch for ch in line if "\u4e00" <= ch <= "\u9fff")
    for start in range(len(chars)):
        for end in range(start + 2, min(start + 5, len(chars) + 1)):
            if is_plausible_tw_name(chars[start:end]):
                return True
    return bool(re.search(r"[A-Z][a-z]{1,20}(?:[ \-][A-Z][a-z]{1,20})+", line))


def _boxes_for_text_hits(
    payload: dict[str, list],
    hits: list,
    image_size: tuple[int, int],
) -> list[SensitiveBox]:
    rows = _ocr_rows(payload)
    joined = "\n".join(line for line, _box in rows)
    ranges: list[tuple[int, int, int]] = []
    cursor = 0
    for index, (line, _box) in enumerate(rows):
        ranges.append((index, cursor, cursor + len(line)))
        cursor += len(line) + 1
    image_width, image_height = image_size
    painted: list[SensitiveBox] = []
    for hit in hits:
        start = int(getattr(hit, "start", 0))
        end = int(getattr(hit, "end", 0))
        entity = str(getattr(hit, "entity_type", "PERSON"))
        span = joined[start:end]
        for index, line_start, line_end in ranges:
            if end <= line_start or start >= line_end:
                continue
            line, box = rows[index]
            if span.strip() and span.strip() not in line and entity == "PERSON":
                if not _line_holds_person_name(line):
                    continue
            sized = SensitiveBox(
                left=box.left,
                top=box.top,
                width=box.width,
                height=box.height,
                entity_type=entity,
            )
            if entity == "PERSON" and _too_large_for_person(sized, image_width, image_height):
                continue
            painted.append(sized)
    return painted


def _visible_rect(box: SensitiveBox, image_width: int, image_height: int) -> tuple[int, int, int, int]:
    pad = 10
    left = max(int(box.left) - pad, 0)
    top = max(int(box.top) - pad, 0)
    right = min(max(left + int(box.width) + pad * 2, left + 36), image_width)
    bottom = min(max(top + int(box.height) + pad * 2, top + 24), image_height)
    return left, top, right, bottom


def images_differ(left: bytes, right: bytes) -> bool:
    """True when RGB pixels differ; used to decide whether chat should show a redacted preview."""
    if not left or not right or left == right:
        return bool(left) != bool(right)
    with Image.open(io.BytesIO(left)) as first, Image.open(io.BytesIO(right)) as second:
        if first.size != second.size:
            return True
        return list(first.convert("RGB").getdata()) != list(second.convert("RGB").getdata())
