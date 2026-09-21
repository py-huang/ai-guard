"""Face redaction for classmate photos. Presidio covers text-in-image, not faces."""

from __future__ import annotations

import io
from collections.abc import Callable, Sequence

import numpy as np
from PIL import Image, ImageDraw

FaceBox = tuple[int, int, int, int]
FaceDetector = Callable[[Image.Image], Sequence[FaceBox]]

_BLACK = (0, 0, 0)
_CASCADE_FILES = (
    "haarcascade_frontalface_default.xml",
    "haarcascade_frontalface_alt2.xml",
    "haarcascade_profileface.xml",
)


def detect_faces_opencv(image: Image.Image) -> list[FaceBox]:
    """Haar cascades shipped with OpenCV in the venv — no extra system package."""
    import cv2

    gray = cv2.cvtColor(np.array(image.convert("RGB")), cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    found: list[FaceBox] = []
    seen: set[tuple[int, int, int, int]] = set()
    for name in _CASCADE_FILES:
        path = f"{cv2.data.haarcascades}{name}"
        classifier = cv2.CascadeClassifier(path)
        if classifier.empty():
            continue
        hits = classifier.detectMultiScale(
            gray,
            scaleFactor=1.08,
            minNeighbors=4,
            minSize=(48, 48),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )
        for x, y, width, height in hits:
            box = tuple(int(v) for v in _pad_box(int(x), int(y), int(width), int(height), image.size))
            if box in seen:
                continue
            seen.add(box)
            found.append(box)
    return _nms(found)


def count_faces_in_bytes(
    image_bytes: bytes,
    detector: FaceDetector | None = None,
) -> int:
    """How many faces Haar (or an injected detector) sees. Invalid images count as 0."""
    if not image_bytes:
        return 0
    try:
        with Image.open(io.BytesIO(image_bytes)) as opened:
            rgb = opened.convert("RGB")
            finder = detector or detect_faces_opencv
            return len(finder(rgb))
    except Exception:
        return 0


def redact_face_boxes(image: Image.Image, boxes: Sequence[FaceBox]) -> Image.Image:
    working = image.convert("RGB").copy()
    draw = ImageDraw.Draw(working)
    for box in boxes:
        draw.ellipse(box, fill=_BLACK)
        draw.rectangle(box, fill=_BLACK)
    return working


def _pad_box(x: int, y: int, width: int, height: int, size: tuple[int, int]) -> FaceBox:
    img_w, img_h = size
    pad_x = int(width * 0.18)
    pad_y = int(height * 0.22)
    left = max(x - pad_x, 0)
    top = max(y - pad_y, 0)
    right = min(x + width + pad_x, img_w)
    bottom = min(y + height + pad_y, img_h)
    return (left, top, right, bottom)


def _nms(boxes: list[FaceBox], iou_threshold: float = 0.35) -> list[FaceBox]:
    if len(boxes) <= 1:
        return boxes
    ordered = sorted(boxes, key=lambda box: (box[2] - box[0]) * (box[3] - box[1]), reverse=True)
    kept: list[FaceBox] = []
    for box in ordered:
        if any(_iou(box, other) > iou_threshold for other in kept):
            continue
        kept.append(box)
    return kept


def _iou(a: FaceBox, b: FaceBox) -> float:
    left = max(a[0], b[0])
    top = max(a[1], b[1])
    right = min(a[2], b[2])
    bottom = min(a[3], b[3])
    inter = max(0, right - left) * max(0, bottom - top)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    return inter / (area_a + area_b - inter)
