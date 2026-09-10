"""Zero-disk image PII redaction via in-memory buffers only."""

from __future__ import annotations

import io
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from PIL import Image

from safety_gateway.pii.faces import FaceBox, detect_faces_opencv, redact_face_boxes
from safety_gateway.pii.ocr import ImageOcrUnavailable, build_ocr, isolate_runtime_caches

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
        if not image_bytes:
            raise ValueError("image_bytes must be a non-empty byte buffer")

        with Image.open(io.BytesIO(image_bytes)) as opened:
            opened.load()
            working = opened.convert("RGB")

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

        output = io.BytesIO()
        redacted.save(output, format="PNG", optimize=True)
        return output.getvalue()

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
