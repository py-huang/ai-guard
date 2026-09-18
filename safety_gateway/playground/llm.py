"""LLM backends for the playground: Gemini when a key exists, echo otherwise."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Callable, Literal

SYSTEM_PROMPT = """你是台灣 K-12 的學習夥伴，不是搜尋引擎、也不是複誦機。

語言與語氣
- 只用繁體中文。句子短、具體、溫暖，像認真聽完的大哥哥大姊姊。
- 先回應小朋友真正想問的事（功課、心情、好奇），再視情況問一個小問題讓他自己想。
- 不要把對方的整段話重複一遍。

個資代號（非常重要）
你會看到 <PERSON_1>、<SCHOOL_1>、<EMAIL_ADDRESS_1>、<CREDIT_CARD_1> 這類 <TYPE_N> 記號。
- 那是系統為了保護兒童而換成的代號。請原封不動使用，不要猜真名、電話、地址、學校全名、身分證、信箱或卡號。
- 不要向小朋友要更多個資（全名、電話、地址、身分證、信箱、卡號、班上同學名單）。
- 如果對方只是在自我介紹，用代號自然打招呼，並邀請他分享「想聊什麼功課或故事」，不要盤問隱私。

安全（台灣兒少保護／分級裡的兒童不宜）
- 不提供或描繪：色情與裸露、性侵或性剝削、血腥殘酷與易模仿暴力、過度恐怖驚嚇、
  自殺自殘與危險挑戰的做法、毒品菸酒檳榔、仇恨歧視言語、真錢賭博。
- 健康教育、性教育、歷史、反毒、菸害防制作業可以討論觀念，但不要給做法或影片來源。
- 若話題不適合兒童，溫柔轉到安全的學習主題，不要複述不當內容。

照片
- 你可能會看到一張已經遮過臉與文字個資的照片。黑塊是保護兒童，不要還原、不要猜那是誰。
- 可以看圖回答功課（植物、題目、地圖），但不要依照片去生成或改真人外貌。
"""

_GEMINI_MODELS = ("gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.8-flash")
_IMAGE_GEN_MODELS = (
    "gemini-3.1-flash-lite-image",
    "gemini-3.1-flash-image",
    "gemini-2.5-flash-image",
)
_CHILD_BUSY = "老師現在有點忙，請稍等再按一次「送出」。過幾秒通常就好了。"
_CHILD_FAIL = "這次沒能連上老師。請再試一次；如果一直不行，請告訴旁邊的大人。"
_CHILD_POLICY = "這次的內容不適合在這裡討論。我們可以改聊功課或今天發生的好事。"
_CHILD_IMAGE_QUOTA = (
    "目前這把 Gemini 金鑰沒有生圖配額（免費方案是 0 次）。"
    "文字聊天可以用。真的要畫圖，請到 Google AI Studio 幫這個專案綁定帳單再試。"
)
_RETRYABLE_MARKERS = (
    "503",
    "unavailable",
    "high demand",
    "overloaded",
    "try again later",
    "429",
    "resource_exhausted",
    "resource exhausted",
    "temporarily",
    "deadline exceeded",
    "504",
    "timeout",
    "503 unavailable",
)
_NOT_FOUND_MARKERS = ("404", "not_found", "not found", "no longer available")


class LlmError(RuntimeError):
    retryable: bool = False
    child_message: str = _CHILD_FAIL


class LlmBusyError(LlmError):
    retryable = True
    child_message = _CHILD_BUSY


class LlmFatalError(LlmError):
    retryable = False
    child_message = _CHILD_FAIL


class LlmPolicyBlockError(LlmError):
    """Gemini safety filter blocked the turn; show a child-safe sentence, do not retry."""

    retryable = False
    child_message = _CHILD_POLICY


class LlmQuotaError(LlmError):
    """Paid image models are listed, but this key's free-tier quota is zero."""

    retryable = False
    child_message = _CHILD_IMAGE_QUOTA


class LlmBackend(ABC):
    name: str
    model: str

    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        image_bytes: bytes | None = None,
    ) -> str:
        """messages: {role: user|assistant, content: str}, already PII-tokenized.

        image_bytes is an optional already-redacted PNG for the latest user turn.
        """

    def generate_image(self, prompt: str) -> tuple[bytes, str]:
        """Return (png_bytes, model_name). Backends that cannot draw raise LlmError."""
        raise LlmFatalError(_CHILD_FAIL)


class EchoLlm(LlmBackend):
    """Deterministic stand-in so the gateway can be exercised without an API key."""

    name = "echo"
    model = "echo-demo"

    def complete(
        self,
        messages: list[dict[str, str]],
        image_bytes: bytes | None = None,
    ) -> str:
        last = next((item["content"] for item in reversed(messages) if item["role"] == "user"), "")
        if last.startswith("【教學模式】"):
            return (
                "我們先不要看完整答案。你可以把題目拆成更小的一步，"
                "再告訴我你會先從哪裡開始？"
            )
        seen = "我有看到你附的照片（系統已先遮掉臉和個資）。" if image_bytes else ""
        return (
            f"小朋友你好，{seen}我聽到你提到：{last}。"
            "如果句子裡有像 <PERSON_1> 這種記號，我會把它當成保護隱私的代號，"
            "不會去猜真正的名字或電話喔。我們可以一起想下一步。"
        )

    def generate_image(self, prompt: str) -> tuple[bytes, str]:
        from safety_gateway.steps.homework_image import render_echo_homework_png

        return render_echo_homework_png(), "echo-demo-image"


class GeminiLlm(LlmBackend):
    name = "gemini"
    model = _GEMINI_MODELS[0]

    def __init__(
        self,
        api_key: str,
        model: str = _GEMINI_MODELS[0],
        max_attempts: int = 3,
        backoff_seconds: float = 0.6,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        from google import genai
        from google.genai import types

        self.model = model
        self._max_attempts = max(1, max_attempts)
        self._backoff_seconds = backoff_seconds
        self._sleep = sleeper
        self._client = genai.Client(api_key=api_key, http_options={"timeout": 60_000})
        self._types = types

    def complete(
        self,
        messages: list[dict[str, str]],
        image_bytes: bytes | None = None,
    ) -> str:
        def generate(model: str) -> str:
            return self._generate(model, messages, image_bytes=image_bytes)

        text, model = complete_with_failover(
            generate,
            models=(self.model, *_GEMINI_MODELS),
            max_attempts=self._max_attempts,
            backoff_seconds=self._backoff_seconds,
            sleeper=self._sleep,
        )
        self.model = model
        return text

    def _generate(
        self,
        model: str,
        messages: list[dict[str, str]],
        image_bytes: bytes | None = None,
    ) -> str:
        last_user = max(
            (index for index, item in enumerate(messages) if item["role"] == "user"),
            default=-1,
        )
        contents = []
        for index, item in enumerate(messages):
            role = "user" if item["role"] == "user" else "model"
            parts = [self._types.Part(text=item["content"])]
            if image_bytes and index == last_user:
                parts.append(
                    self._types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                )
            contents.append(self._types.Content(role=role, parts=parts))
        response = self._client.models.generate_content(
            model=model,
            contents=contents,
            config=self._types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
                safety_settings=_gemini_child_safety_settings(self._types),
            ),
        )
        if _gemini_blocked(response):
            raise LlmPolicyBlockError(_CHILD_POLICY)
        try:
            text = (response.text or "").strip()
        except Exception as exc:
            raise LlmPolicyBlockError(_CHILD_POLICY) from exc
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text

    def generate_image(self, prompt: str) -> tuple[bytes, str]:
        def generate(model: str) -> bytes:
            return self._generate_image(model, prompt)

        png, model = complete_with_failover(
            generate,  # type: ignore[arg-type]
            models=_IMAGE_GEN_MODELS,
            max_attempts=self._max_attempts,
            backoff_seconds=self._backoff_seconds,
            sleeper=self._sleep,
        )
        return png, model  # type: ignore[return-value]

    def _generate_image(self, model: str, prompt: str) -> bytes:
        response = self._client.models.generate_content(
            model=model,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                system_instruction=(
                    "Create a child-safe educational illustration. "
                    "No people, no faces, no photorealistic humans, no violence."
                ),
                response_modalities=["IMAGE"],
                image_config=self._types.ImageConfig(
                    aspect_ratio="1:1",
                ),
                safety_settings=_gemini_child_safety_settings(self._types),
            ),
        )
        if _gemini_blocked(response):
            raise LlmPolicyBlockError(_CHILD_POLICY)
        blob = _inline_image_bytes(response)
        if not blob:
            raise LlmPolicyBlockError(_CHILD_POLICY)
        return blob


def complete_with_failover(
    generate: Callable[[str], str],
    models: tuple[str, ...],
    max_attempts: int = 3,
    backoff_seconds: float = 0.6,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[str, str]:
    last_error: Exception | None = None
    tried: list[str] = []
    for model in models:
        if model in tried:
            continue
        tried.append(model)
        for attempt in range(max_attempts):
            try:
                return generate(model), model
            except Exception as exc:
                last_error = exc
                if isinstance(exc, LlmError):
                    raise
                if _is_zero_quota(exc):
                    raise LlmQuotaError(_CHILD_IMAGE_QUOTA) from exc
                if _is_not_found(exc):
                    break
                if _is_retryable(exc) and attempt < max_attempts - 1:
                    sleeper(backoff_seconds * (2**attempt))
                    continue
                if not _is_retryable(exc):
                    raise LlmFatalError(_CHILD_FAIL) from exc
                break
    if last_error is not None and _is_not_found(last_error):
        raise LlmFatalError(_CHILD_FAIL) from last_error
    raise LlmBusyError(_CHILD_BUSY) from last_error


def is_retryable_llm_error(exc: BaseException) -> bool:
    return isinstance(exc, LlmBusyError) or _is_retryable(exc)


def child_safe_llm_message(exc: BaseException) -> str:
    if isinstance(exc, LlmError):
        return exc.child_message
    if _is_retryable(exc):
        return _CHILD_BUSY
    return _CHILD_FAIL


def _is_retryable(exc: BaseException) -> bool:
    blob = _error_blob(exc)
    return any(marker in blob for marker in _RETRYABLE_MARKERS)


def _is_not_found(exc: BaseException) -> bool:
    blob = _error_blob(exc)
    return any(marker in blob for marker in _NOT_FOUND_MARKERS)


def _is_zero_quota(exc: BaseException) -> bool:
    blob = _error_blob(exc)
    return "limit: 0" in blob and ("free_tier" in blob or "quota" in blob)


def _error_blob(exc: BaseException) -> str:
    parts = [str(exc), type(exc).__name__]
    cause = getattr(exc, "__cause__", None)
    if cause is not None:
        parts.append(str(cause))
    code = getattr(exc, "code", None)
    if code is not None:
        parts.append(str(code))
    status = getattr(exc, "status", None)
    if status is not None:
        parts.append(str(status))
    return " ".join(parts).lower()


def _gemini_child_safety_settings(types: object) -> list[object]:
    """Block low-and-above on Gemini harm categories that overlap Taiwan child ratings."""
    threshold = types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE  # type: ignore[attr-defined]
    categories = (
        types.HarmCategory.HARM_CATEGORY_HARASSMENT,  # type: ignore[attr-defined]
        types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,  # type: ignore[attr-defined]
        types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,  # type: ignore[attr-defined]
        types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,  # type: ignore[attr-defined]
    )
    return [
        types.SafetySetting(category=category, threshold=threshold)  # type: ignore[attr-defined]
        for category in categories
    ]


def _inline_image_bytes(response: object) -> bytes | None:
    candidates = getattr(response, "candidates", None) or ()
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or ()
        for part in parts:
            inline = getattr(part, "inline_data", None)
            data = getattr(inline, "data", None) if inline is not None else None
            if data:
                return bytes(data)
    return None


def _gemini_blocked(response: object) -> bool:
    prompt_feedback = getattr(response, "prompt_feedback", None)
    block_reason = getattr(prompt_feedback, "block_reason", None) if prompt_feedback else None
    if block_reason not in (None, 0, "", "BLOCK_REASON_UNSPECIFIED"):
        return True
    candidates = getattr(response, "candidates", None) or ()
    for candidate in candidates:
        finish = str(getattr(candidate, "finish_reason", "") or "")
        if "SAFETY" in finish.upper():
            return True
    return False


def resolve_backend(api_key: str | None) -> LlmBackend:
    key = (api_key or "").strip()
    if not key:
        return EchoLlm()
    return GeminiLlm(api_key=key)


def backend_status(api_key: str | None) -> tuple[Literal["gemini", "echo"], str]:
    backend = resolve_backend(api_key)
    return backend.name, backend.model  # type: ignore[return-value]
