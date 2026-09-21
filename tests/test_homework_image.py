from __future__ import annotations

import base64

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.playground.llm import EchoLlm
from safety_gateway.playground.service import PlaygroundChat
from safety_gateway.steps.content_safety import ContentSafetyStep
from safety_gateway.steps.homework_image import image_gen_action, render_echo_homework_png
from safety_gateway.vault.memory import InMemorySessionVault


def test_image_gen_intent_generates_unless_denied() -> None:
    assert image_gen_action("請幫我畫一朵花，自然課要用。") == "generate"
    assert image_gen_action("畫一個三角形") == "generate"
    assert image_gen_action("幫我產生今天天氣的圖片") == "generate"
    assert image_gen_action("請幫我畫一台車子") == "generate"
    assert image_gen_action("產生身分證的圖片") == "refuse"
    assert image_gen_action("我叫王小明，我在中山國小上課") == "chat"


def test_drawing_a_child_face_is_blocked_before_imagen() -> None:
    step = ContentSafetyStep()
    match = step.classify("請幫我畫一個小朋友的臉。")
    assert match is not None
    assert match.category == "image_abuse"
    inbound = AISafetyGateway().process_inbound("draw-kid", "請幫我畫一個小朋友的臉。")
    assert inbound.blocked is True
    assert inbound.block_category == "image_abuse"


def test_playground_echo_returns_homework_png() -> None:
    chat = PlaygroundChat(AISafetyGateway(vault=InMemorySessionVault()))
    turn = chat.chat("draw-1", "請幫我畫一朵花，自然課要用。", EchoLlm(), enable_images=True)
    assert turn.blocked is False
    assert turn.image_generated is True
    assert turn.generated_image_base64
    raw = base64.b64decode(turn.generated_image_base64)
    assert raw.startswith(b"\x89PNG")
    assert raw == render_echo_homework_png()
    assert "幫你畫的圖" in turn.child_reply
    stored = chat.evidence("draw-1")[0]
    assert stored.image_generated is True
    assert stored.generated_image_base64 is None


def test_weather_picture_request_goes_to_image_model() -> None:
    class Probe(EchoLlm):
        def __init__(self) -> None:
            self.prompts: list[str] = []

        def generate_image(self, prompt: str) -> tuple[bytes, str]:
            self.prompts.append(prompt)
            return super().generate_image(prompt)

        def complete(self, messages: list[dict[str, str]], image_bytes: bytes | None = None) -> str:
            raise AssertionError("weather picture must not go to the text model")

    probe = Probe()
    turn = PlaygroundChat(AISafetyGateway()).chat(
        "draw-wx", "幫我產生今天天氣的圖片", probe, enable_images=True
    )
    assert turn.image_generated is True
    assert probe.prompts
    assert "weather" in probe.prompts[0].lower() or "天氣" in probe.prompts[0]


def test_stable_chat_does_not_call_image_model() -> None:
    class Probe(EchoLlm):
        def __init__(self) -> None:
            self.draws = 0

        def generate_image(self, prompt: str) -> tuple[bytes, str]:
            self.draws += 1
            return super().generate_image(prompt)

    probe = Probe()
    turn = PlaygroundChat(AISafetyGateway()).chat("draw-stable", "幫我產生今天天氣的圖片", probe)
    assert probe.draws == 0
    assert turn.image_generated is False
    assert turn.llm_backend == "echo"


def test_id_photo_request_does_not_call_image_model() -> None:
    class Probe(EchoLlm):
        def __init__(self) -> None:
            self.draws = 0

        def generate_image(self, prompt: str) -> tuple[bytes, str]:
            self.draws += 1
            return super().generate_image(prompt)

    probe = Probe()
    turn = PlaygroundChat(AISafetyGateway()).chat(
        "draw-2", "產生身分證的圖片", probe, enable_images=True
    )
    assert probe.draws == 0
    assert turn.image_generated is False
    assert turn.generated_image_base64 is None
    assert "不能畫真人" in turn.child_reply
    assert turn.blocked is False


def test_image_model_busy_does_not_fake_a_gemini_png() -> None:
    from safety_gateway.playground.llm import LlmBusyError

    class BusyDraw(EchoLlm):
        def generate_image(self, prompt: str) -> tuple[bytes, str]:
            raise LlmBusyError()

    turn = PlaygroundChat(AISafetyGateway()).chat(
        "draw-busy", "請幫我畫一朵花，自然課要用。", BusyDraw(), enable_images=True
    )
    assert turn.blocked is False
    assert turn.image_generated is False
    assert turn.generated_image_base64 is None
    assert turn.llm_model == "unavailable"
    assert "忙" in turn.child_reply


def test_image_quota_zero_explains_billing() -> None:
    from safety_gateway.playground.llm import LlmQuotaError

    class QuotaDraw(EchoLlm):
        def generate_image(self, prompt: str) -> tuple[bytes, str]:
            raise LlmQuotaError()

    turn = PlaygroundChat(AISafetyGateway()).chat(
        "draw-quota", "幫我產生今天天氣的圖片", QuotaDraw(), enable_images=True
    )
    assert turn.image_generated is False
    assert turn.generated_image_base64 is None
    assert turn.llm_model == "quota"
    assert "配額" in turn.child_reply
    assert "帳單" in turn.child_reply
