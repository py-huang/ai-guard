"""Zero-disk image PII redaction via in-memory buffers only."""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

from PIL import Image

if TYPE_CHECKING:
    from presidio_analyzer import AnalyzerEngine, PatternRecognizer
    from presidio_image_redactor import ImageRedactorEngine


PNG_CONTENT_TYPE = "image/png"
_BLACK_FILL = (0, 0, 0)


class ImageOcrUnavailable(RuntimeError):
    """Raised when Presidio image redaction cannot run because OCR is missing."""


class InMemoryImageRedactor:
    """Redact PII from uploaded photos without writing the source image to disk."""

    def __init__(
        self,
        engine: ImageRedactorEngine | None = None,
        analyzer_engine: AnalyzerEngine | None = None,
        ad_hoc_recognizers: list[PatternRecognizer] | None = None,
    ) -> None:
        self._engine = engine
        self._analyzer_engine = analyzer_engine
        self._ad_hoc_recognizers = ad_hoc_recognizers

    def redact_image_in_memory(self, image_bytes: bytes) -> bytes:
        if not image_bytes:
            raise ValueError("image_bytes must be a non-empty byte buffer")

        with Image.open(io.BytesIO(image_bytes)) as opened:
            opened.load()
            working = opened.convert("RGB")

        try:
            redacted = self._engine_instance().redact(
                working,
                fill=_BLACK_FILL,
                ocr_kwargs={"lang": "chi_tra+eng"},
                ad_hoc_recognizers=self._ad_hoc_recognizers,
                language="zh",
            )
        except Exception as exc:
            blob = str(exc).lower()
            if "tesseract" in blob:
                raise ImageOcrUnavailable(
                    "這台電腦還沒裝 Tesseract OCR，無法辨識照片上的文字。"
                    "請改用「示範聯絡簿」（不需 OCR），或安裝 tesseract 與 chi_tra 語言包。"
                ) from exc
            raise

        output = io.BytesIO()
        redacted.save(output, format="PNG", optimize=True)
        return output.getvalue()

    def _engine_instance(self) -> ImageRedactorEngine:
        if self._engine is not None:
            return self._engine
        from presidio_image_redactor import ImageAnalyzerEngine, ImageRedactorEngine

        image_analyzer = None
        if self._analyzer_engine is not None:
            image_analyzer = ImageAnalyzerEngine(analyzer_engine=self._analyzer_engine)
        self._engine = ImageRedactorEngine(image_analyzer_engine=image_analyzer)
        return self._engine
