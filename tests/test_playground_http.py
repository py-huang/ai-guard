from __future__ import annotations

from fastapi.testclient import TestClient

from safety_gateway.pii.demo_image import render_contact_book
from safety_gateway.playground.app import create_app
from safety_gateway.playground.features import FEATURES
from safety_gateway.playground.llm import LlmBusyError
from safety_gateway.playground.service import PlaygroundChat


def test_all_inventory_features_are_shipped() -> None:
    assert FEATURES
    assert all(item["status"] == "shipped" for item in FEATURES)
    assert "presidio_defaults_zh" in {item["id"] for item in FEATURES}


def test_chat_page_exposes_new_pii_chips() -> None:
    client = TestClient(create_app())
    page = client.get("/")
    assert page.status_code == 200
    assert "信箱 + 卡號" in page.text
    assert "健康教育（應放行）" in page.text
    assert "presidio_defaults_zh" in client.get("/api/features").text


def test_generated_photo_is_served() -> None:
    client = TestClient(create_app())
    response = client.get("/api/generated-image")
    assert response.status_code == 200
    assert response.content.startswith(b"\x89PNG")


def test_demo_image_endpoint_returns_png() -> None:
    client = TestClient(create_app())
    original = client.get("/api/demo-image")
    redacted = client.get("/api/demo-image", params={"redacted": True})
    assert original.status_code == 200
    assert redacted.status_code == 200
    assert original.content.startswith(b"\x89PNG")
    assert redacted.content.startswith(b"\x89PNG")
    assert original.content != redacted.content


def test_upload_redact_uses_venv_ocr() -> None:
    client = TestClient(create_app())
    original, _boxes = render_contact_book()
    response = client.post(
        "/api/redact-image",
        params={"session_id": "img-upload-1"},
        files={"file": ("contact-book.png", original, "image/png")},
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"\x89PNG")
    assert response.content != original


def test_classmate_photo_ocr_endpoint() -> None:
    client = TestClient(create_app())
    original = client.get("/api/classmate-image")
    redacted = client.post(
        "/api/redact-classmate-image",
        params={"session_id": "img-classmate-1"},
    )
    assert original.status_code == 200
    assert redacted.status_code == 200, redacted.text
    assert original.content.startswith(b"\x89PNG")
    assert redacted.content.startswith(b"\x89PNG")
    assert redacted.content != original.content


def test_generated_photo_ocr_endpoint() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/redact-generated-image",
        params={"session_id": "img-gen-1"},
    )
    assert response.status_code == 200, response.text
    assert response.content.startswith(b"\x89PNG")


def test_chat_busy_returns_child_safe_json(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def boom(self, session_id: str, text: str, llm: object) -> object:
        raise LlmBusyError("老師現在有點忙，請稍等再按一次「送出」。過幾秒通常就好了。")

    monkeypatch.setattr(PlaygroundChat, "chat", boom)
    client = TestClient(create_app())
    response = client.post("/api/chat", json={"session_id": "http-1", "text": "你好"})
    assert response.status_code == 503
    payload = response.json()["detail"]
    assert payload["retryable"] is True
    assert "忙" in payload["message"]
    assert "503" not in payload["message"]
    assert "UNAVAILABLE" not in payload["message"]
    assert "high demand" not in payload["message"]
