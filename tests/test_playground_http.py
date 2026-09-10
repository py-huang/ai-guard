from __future__ import annotations

from fastapi.testclient import TestClient

from safety_gateway.playground.app import create_app
from safety_gateway.playground.features import FEATURES
from safety_gateway.playground.llm import LlmBusyError
from safety_gateway.playground.service import PlaygroundChat


def test_all_inventory_features_are_shipped() -> None:
    assert FEATURES
    assert all(item["status"] == "shipped" for item in FEATURES)


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
