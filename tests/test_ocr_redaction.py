from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from PIL import Image

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.demo_image import generated_fixture_path, render_contact_book
from safety_gateway.pii.ocr import isolate_runtime_caches, ocr_lines

pytest.importorskip("rapidocr_onnxruntime")

_SECRETS = ("王小明", "0912-345-678", "A123456789", "中山國小")


def test_ocr_runtime_stays_inside_venv() -> None:
    cache = isolate_runtime_caches()
    assert Path(sys.prefix) in cache.parents or cache.parent == Path(sys.prefix)
    assert cache.is_dir()


def test_ocr_reads_demo_contact_book() -> None:
    original, _boxes = render_contact_book()
    blob = "".join(ocr_lines(original))
    for secret in _SECRETS:
        assert secret in blob


def test_ocr_redaction_hides_pii_on_second_pass() -> None:
    original, _boxes = render_contact_book()
    redacted = AISafetyGateway().redact_image_in_memory(original)
    assert redacted.startswith(b"\x89PNG")
    remaining = "".join(ocr_lines(redacted))
    for secret in _SECRETS:
        assert secret not in remaining, remaining


def test_ocr_redaction_hides_pii_on_generated_photo() -> None:
    path = generated_fixture_path()
    assert path is not None
    original = path.read_bytes()
    before = "".join(ocr_lines(original))
    assert "王小明" in before
    assert "0912-345-678" in before
    redacted = AISafetyGateway().redact_image_in_memory(original)
    remaining = "".join(ocr_lines(redacted))
    assert "王小明" not in remaining, remaining
    assert "0912-345-678" not in remaining, remaining
    assert "A123456789" not in remaining, remaining
    with Image.open(io.BytesIO(redacted)) as image:
        assert image.format == "PNG"
