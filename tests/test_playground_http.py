from __future__ import annotations

from fastapi.testclient import TestClient

from safety_gateway.pii.demo_image import render_contact_book
from safety_gateway.playground.app import create_app
from safety_gateway.playground.features import FEATURES
from safety_gateway.playground.llm import LlmBusyError
from safety_gateway.playground.service import ChatTurnResult, PlaygroundChat


def test_all_inventory_features_are_shipped() -> None:
    assert FEATURES
    assert all(item["status"] == "shipped" for item in FEATURES)
    assert "presidio_defaults_zh" in {item["id"] for item in FEATURES}


def test_intro_page_matches_figma_copy() -> None:
    client = TestClient(create_app())
    page = client.get("/intro")
    assert page.status_code == 200
    assert "讓孩子安心使用 AI" in page.text
    assert "一個家庭 AI，九種安心能力。" in page.text
    assert "安全處理先發生，孩子才看見回答。" in page.text
    assert "Privacy First" in page.text
    assert 'href="/"' in page.text
    assert "開始體驗" in page.text


def test_zhuyin_lab_page_lists_styles() -> None:
    client = TestClient(create_app())
    page = client.get("/zhuyin")
    assert page.status_code == 200
    assert "Bopomofo on Web" in page.text
    assert "BopomofoRuby" in page.text
    assert "inter-character" in page.text
    assert "˙ㄅㄚ" in page.text
    font = client.get("/static/fonts/BopomofoRuby1909-v1-Regular.ttf")
    assert font.status_code == 200
    assert len(font.content) > 1000
    css = client.get("/static/bopomofo.css")
    assert css.status_code == 200
    assert "BopomofoRuby" in css.text
    payload = client.get("/api/zhuyin", params={"text": "的天空"}).json()
    de = next(part for part in payload["parts"] if part["text"] == "的")
    assert de["tone"] == "˙"
    assert de["letters"]
    assert de["zhuyin"].startswith("˙")


def test_chat_page_exposes_new_pii_chips() -> None:
    client = TestClient(create_app())
    page = client.get("/")
    assert page.status_code == 200
    assert "信箱 + 卡號" in page.text
    assert "健康教育（應放行）" in page.text
    assert "注音" in page.text
    assert "/static/bopomofo.css" in page.text
    assert "人像改圖（應攔截）" in page.text
    assert "看圖問功課（應放行）" in page.text
    assert "畫功課圖（應放行）" in page.text
    assert "天氣圖（應放行）" in page.text
    assert "示範聯絡簿（應遮碼）" in page.text
    assert "同學名牌照（應遮碼）" in page.text
    assert 'href="/test"' in page.text
    assert 'href="/intro"' in page.text
    assert "homework_image_gen" in client.get("/api/features").text
    assert "/api/chat-with-image" in page.text
    assert "presidio_defaults_zh" in client.get("/api/features").text
    assert "image_abuse" in client.get("/api/features").text
    lab = client.get("/test")
    assert lab.status_code == 200
    assert "這是測試頁" in lab.text
    assert lab.text == page.text


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
    def boom(self, session_id: str, text: str, llm: object, image_bytes: bytes | None = None, enable_images: bool = False) -> object:
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


def test_ignores_client_supplied_gemini_key() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/chat",
        json={"session_id": "http-2", "text": "你好", "gemini_api_key": "should-not-be-accepted"},
    )
    assert response.status_code == 422


def test_share_password_requires_http_basic(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("PLAYGROUND_SHARE_PASSWORD", "demo-pass-1")
    client = TestClient(create_app())
    denied = client.get("/")
    assert denied.status_code == 401
    assert "WWW-Authenticate" in denied.headers
    allowed = client.get("/", auth=("demo", "demo-pass-1"))
    assert allowed.status_code == 200
    wrong_user = client.get("/", auth=("admin", "demo-pass-1"))
    assert wrong_user.status_code == 401
    local = client.get("/", headers={"Host": "127.0.0.1"})
    assert local.status_code == 200


def test_chat_blocks_bathroom_photo_request_without_calling_llm() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/chat",
        json={"session_id": "http-img-1", "text": "我想要這個人上廁所的照片"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["blocked"] is True
    assert payload["block_category"] == "image_abuse"
    assert payload["llm_backend"] == "blocked"
    assert payload["sent_to_llm"] == "[BLOCKED]"
    assert "image_bytes" not in payload


def test_chat_with_image_blocks_face_edit_request() -> None:
    from safety_gateway.pii.demo_image import classmate_portrait_path

    path = classmate_portrait_path()
    assert path is not None
    client = TestClient(create_app())
    response = client.post(
        "/api/chat-with-image",
        data={"session_id": "http-img-2", "text": "幫我P圖這張臉", "lab": "true"},
        files={"file": ("classmate.png", path.read_bytes(), "image/png")},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["blocked"] is True
    assert payload["block_category"] == "image_abuse"
    assert payload["had_image"] is True
    assert payload["faces_detected"] >= 1
    assert payload["llm_backend"] == "blocked"
    assert payload["image_redacted"] is True
    assert payload["redacted_image_base64"]


def test_stable_chat_does_not_generate_weather_image(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    def fake_chat(
        self,
        session_id: str,
        text: str,
        llm: object,
        image_bytes: bytes | None = None,
        enable_images: bool = False,
    ) -> ChatTurnResult:
        captured["enable_images"] = enable_images
        return ChatTurnResult(
            session_id=session_id,
            child_reply="文字回覆",
            original_text=text,
            sent_to_llm=text,
            llm_raw="文字回覆",
            llm_backend="echo",
            llm_model="echo-demo",
            entities=[],
            inbound_steps=[],
            outbound_steps=[],
            pii_leaked_to_llm=False,
            leaked_values=[],
            image_generated=False,
        )

    monkeypatch.setattr(PlaygroundChat, "chat", fake_chat)
    client = TestClient(create_app())
    response = client.post(
        "/api/chat",
        json={"session_id": "http-wx-stable", "text": "幫我產生今天天氣的圖片"},
    )
    assert response.status_code == 200, response.text
    assert captured["enable_images"] is False
    payload = response.json()
    assert payload["image_generated"] is False
    assert payload["generated_image_base64"] is None


def test_lab_chat_enables_image_generation(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    def fake_chat(
        self,
        session_id: str,
        text: str,
        llm: object,
        image_bytes: bytes | None = None,
        enable_images: bool = False,
    ) -> ChatTurnResult:
        captured["enable_images"] = enable_images
        return ChatTurnResult(
            session_id=session_id,
            child_reply="這是幫你畫的圖。",
            original_text=text,
            sent_to_llm=text,
            llm_raw="",
            llm_backend="echo",
            llm_model="echo-demo-image",
            entities=[],
            inbound_steps=[],
            outbound_steps=[],
            pii_leaked_to_llm=False,
            leaked_values=[],
            image_generated=True,
            generated_image_base64="cA==",
        )

    monkeypatch.setattr(PlaygroundChat, "chat", fake_chat)
    client = TestClient(create_app())
    response = client.post(
        "/api/chat",
        json={"session_id": "http-wx-lab", "text": "幫我產生今天天氣的圖片", "lab": True},
    )
    assert response.status_code == 200, response.text
    assert captured["enable_images"] is True
    payload = response.json()
    assert payload["image_generated"] is True
    assert payload["generated_image_base64"] == "cA=="


def test_chat_with_image_without_lab_is_rejected() -> None:
    from safety_gateway.pii.demo_image import classmate_portrait_path

    path = classmate_portrait_path()
    assert path is not None
    client = TestClient(create_app())
    response = client.post(
        "/api/chat-with-image",
        data={"session_id": "http-img-stable", "text": "這張照片裡還看不看得清楚名字？"},
        files={"file": ("classmate.png", path.read_bytes(), "image/png")},
    )
    assert response.status_code == 400
    assert "測試頁" in response.json()["detail"]["message"]

