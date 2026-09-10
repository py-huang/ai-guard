"""Venv-isolated OCR for image PII: RapidOCR ONNX models live in site-packages."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from presidio_image_redactor.ocr import OCR


def isolate_runtime_caches() -> Path:
    """Keep matplotlib / ONNX caches inside the active environment prefix."""
    cache = Path(sys.prefix) / "ai-guard-cache"
    mpl = cache / "mpl"
    mpl.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl))
    os.environ.setdefault("XDG_CACHE_HOME", str(cache))
    os.environ.setdefault("ORT_LOG_SEVERITY_LEVEL", "3")
    return cache


isolate_runtime_caches()


class ImageOcrUnavailable(RuntimeError):
    """Raised when no venv OCR backend can be constructed."""


class RapidOcrEngine(OCR):
    """Presidio OCR adapter. Models are bundled in the venv, not a system Tesseract."""

    name = "rapidocr"
    _shared = None

    def __init__(self) -> None:
        self._engine = None

    def perform_ocr(self, image: object, **kwargs: object) -> dict:
        array = _as_rgb_array(image)
        result, _elapsed = self._rapid().__call__(array)
        payload: dict[str, list] = {
            "left": [],
            "top": [],
            "width": [],
            "height": [],
            "text": [],
            "conf": [],
        }
        if not result:
            return payload
        for box, text, score in result:
            xs = [point[0] for point in box]
            ys = [point[1] for point in box]
            left = max(int(min(xs)) - 4, 0)
            top = max(int(min(ys)) - 4, 0)
            payload["left"].append(left)
            payload["top"].append(top)
            payload["width"].append(max(int(max(xs)) - left + 4, 1))
            payload["height"].append(max(int(max(ys)) - top + 4, 1))
            payload["text"].append(str(text))
            payload["conf"].append(float(score) * 100.0)
        return payload

    def _rapid(self):
        if RapidOcrEngine._shared is None:
            from rapidocr_onnxruntime import RapidOCR

            RapidOcrEngine._shared = RapidOCR()
        self._engine = RapidOcrEngine._shared
        return self._engine


def build_ocr() -> OCR:
    try:
        import rapidocr_onnxruntime  # noqa: F401
    except ImportError as exc:
        raise ImageOcrUnavailable(
            "虛擬環境還沒裝 RapidOCR。請在專案 .venv 執行："
            " pip install rapidocr-onnxruntime"
        ) from exc
    return RapidOcrEngine()


def ocr_lines(image_bytes: bytes) -> list[str]:
    """Return recognized lines; used by tests and status checks."""
    with Image.open(io.BytesIO(image_bytes)) as opened:
        opened.load()
        array = np.array(opened.convert("RGB"))
    engine = RapidOcrEngine()
    result, _elapsed = engine._rapid()(array)
    if not result:
        return []
    return [str(item[1]) for item in result]


def _as_rgb_array(image: object) -> np.ndarray:
    if isinstance(image, str):
        with Image.open(image) as opened:
            opened.load()
            return np.array(opened.convert("RGB"))
    if isinstance(image, Image.Image):
        return np.array(image.convert("RGB"))
    array = np.asarray(image)
    if array.ndim == 2:
        return np.stack([array, array, array], axis=-1)
    return array
