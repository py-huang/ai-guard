"""Zero-disk image PII redaction via in-memory buffers only."""

from __future__ import annotations

import io
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from PIL import Image

from safety_gateway.pii.faces import FaceBox, detect_faces_opencv, redact_face_boxes
from safety_gateway.pii.image_forbid import extra_forbid_entities
from safety_gateway.pii.image_sensitive import detect_sensitive_boxes, ocr_payload_to_boxes
from safety_gateway.pii.ocr import ImageOcrUnavailable, build_ocr, isolate_runtime_caches, ocr_payload

if TYPE_CHECKING:
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer
    from presidio_image_redactor import ImageRedactorEngine


PNG_CONTENT_TYPE = "image/png"
_BLACK_FILL = (0, 0, 0)

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

        try:
            redacted = self._engine_instance().redact(
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

        if extra_boxes:
            from PIL import ImageDraw

            draw = ImageDraw.Draw(redacted)
            for box in extra_boxes:
                draw.rectangle(
                    [box.left, box.top, box.left + box.width, box.top + box.height],
                    fill=_BLACK_FILL,
                )
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
            if text and self._analyzer_engine is not None:
                hits = self._analyzer_engine.analyze(text=text, language="zh")
                found.update(hit.entity_type for hit in hits if getattr(hit, "entity_type", None))
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


def images_differ(left: bytes, right: bytes) -> bool:
    """True when RGB pixels differ; used to decide whether chat should show a redacted preview."""
    if not left or not right or left == right:
        return bool(left) != bool(right)
    with Image.open(io.BytesIO(left)) as first, Image.open(io.BytesIO(right)) as second:
        if first.size != second.size:
            return True
        return list(first.convert("RGB").getdata()) != list(second.convert("RGB").getdata())
