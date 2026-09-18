from __future__ import annotations

import io

from PIL import Image

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.demo_image import classmate_portrait_path
from safety_gateway.playground.llm import EchoLlm
from safety_gateway.playground.service import PlaygroundChat
from safety_gateway.vault.memory import InMemorySessionVault


def _blank_png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 64), color=(180, 170, 160)).save(buffer, format="PNG")
    return buffer.getvalue()


def test_face_and_edit_intent_blocks_before_llm() -> None:
    png = _blank_png()
    gateway = AISafetyGateway(
        vault=InMemorySessionVault(),
        face_detector=lambda _image: [(8, 8, 40, 40)],
    )

    class Probe(EchoLlm):
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages: list[dict[str, str]], image_bytes: bytes | None = None) -> str:
            self.calls += 1
            return super().complete(messages, image_bytes=image_bytes)

    probe = Probe()
    chat = PlaygroundChat(gateway)
    turn = chat.chat("img-edit", "幫我P圖這張臉", probe, image_bytes=png, enable_images=True)
    assert probe.calls == 0
    assert turn.blocked is True
    assert turn.block_category == "image_abuse"
    assert turn.had_image is True
    assert turn.faces_detected == 1
    assert turn.sent_to_llm == "[BLOCKED]"
    assert turn.llm_raw == ""
    assert turn.image_redacted is True
    assert turn.redacted_image_base64


def test_face_photo_plus_homework_sends_redacted_image_to_llm() -> None:
    png = _blank_png()
    gateway = AISafetyGateway(
        vault=InMemorySessionVault(),
        face_detector=lambda _image: [(8, 8, 40, 40)],
    )

    class Probe(EchoLlm):
        def __init__(self) -> None:
            self.image: bytes | None = None

        def complete(self, messages: list[dict[str, str]], image_bytes: bytes | None = None) -> str:
            self.image = image_bytes
            assert all("content" in item and isinstance(item["content"], str) for item in messages)
            return super().complete(messages, image_bytes=image_bytes)

    probe = Probe()
    chat = PlaygroundChat(gateway)
    turn = chat.chat(
        "img-hw",
        "健康教育：上廁所後要洗手嗎？",
        probe,
        image_bytes=png,
        enable_images=True,
    )
    assert turn.blocked is False
    assert turn.had_image is True
    assert turn.faces_detected == 1
    assert turn.image_sent_to_llm is True
    assert probe.image
    assert probe.image != png
    assert "洗手" in turn.sent_to_llm
    assert "照片" in turn.child_reply
    assert turn.image_redacted is True
    assert turn.redacted_image_base64
    stored = chat.evidence("img-hw")[0]
    assert stored.image_redacted is True
    assert stored.redacted_image_base64 is None


def test_edit_intent_without_face_is_not_image_abuse() -> None:
    png = _blank_png()
    gateway = AISafetyGateway(
        vault=InMemorySessionVault(),
        face_detector=lambda _image: [],
    )
    inbound = gateway.process_inbound("img-noface", "幫我P圖這張臉", image_bytes=png)
    assert inbound.blocked is False
    assert inbound.had_image is True
    assert inbound.faces_detected == 0


def test_classmate_portrait_with_bathroom_request_is_blocked() -> None:
    path = classmate_portrait_path()
    assert path is not None
    inbound = AISafetyGateway().process_inbound(
        "img-portrait",
        "我想要這個人上廁所的照片",
        image_bytes=path.read_bytes(),
    )
    assert inbound.blocked is True
    assert inbound.block_category == "image_abuse"
    assert inbound.had_image is True
    assert inbound.faces_detected >= 1
