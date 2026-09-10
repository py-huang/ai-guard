"""LLM backends for the playground: Gemini when a key exists, echo otherwise."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

SYSTEM_PROMPT = """你是台灣 K-12 的學習夥伴，不是搜尋引擎、也不是複誦機。

語言與語氣
- 只用繁體中文。句子短、具體、溫暖，像認真聽完的大哥哥大姊姊。
- 先回應小朋友真正想問的事（功課、心情、好奇），再視情況問一個小問題讓他自己想。
- 不要把對方的整段話重複一遍。

個資代號（非常重要）
你會看到 <PERSON_1>、<SCHOOL_1>、<PHONE_NUMBER_1>、<TW_ID_1>、<LOCATION_1> 這類記號。
- 那是系統為了保護兒童而換成的代號。請原封不動使用，不要猜真名、電話、地址、學校全名或身分證。
- 不要向小朋友要更多個資（全名、電話、地址、身分證、班上同學名單）。
- 如果對方只是在自我介紹，用代號自然打招呼，並邀請他分享「想聊什麼功課或故事」，不要盤問隱私。

安全
- 不提供危險、成人或違法指示。若話題不適合兒童，溫柔轉到安全的學習主題。
"""

_GEMINI_MODELS = ("gemini-3.6-flash", "gemini-3.5-flash", "gemini-3.8-flash")


class LlmBackend(ABC):
    name: str
    model: str

    @abstractmethod
    def complete(self, messages: list[dict[str, str]]) -> str:
        """messages: {role: user|assistant, content: str}, already PII-tokenized."""


class EchoLlm(LlmBackend):
    """Deterministic stand-in so the gateway can be exercised without an API key."""

    name = "echo"
    model = "echo-demo"

    def complete(self, messages: list[dict[str, str]]) -> str:
        last = next((item["content"] for item in reversed(messages) if item["role"] == "user"), "")
        return (
            f"小朋友你好，我聽到你提到：{last}。"
            "如果句子裡有像 <PERSON_1> 這種記號，我會把它當成保護隱私的代號，"
            "不會去猜真正的名字或電話喔。我們可以一起想下一步。"
        )


class GeminiLlm(LlmBackend):
    name = "gemini"
    model = _GEMINI_MODELS[0]

    def __init__(self, api_key: str, model: str = _GEMINI_MODELS[0]) -> None:
        from google import genai
        from google.genai import types

        self.model = model
        self._client = genai.Client(api_key=api_key, http_options={"timeout": 45_000})
        self._types = types

    def complete(self, messages: list[dict[str, str]]) -> str:
        last_error: Exception | None = None
        tried: list[str] = []
        for model in (self.model, *_GEMINI_MODELS):
            if model in tried:
                continue
            tried.append(model)
            try:
                text = self._generate(model, messages)
                self.model = model
                return text
            except Exception as exc:  # pragma: no cover - network/model availability
                last_error = exc
                continue
        raise RuntimeError(f"Gemini 無法完成回覆：{last_error}") from last_error

    def _generate(self, model: str, messages: list[dict[str, str]]) -> str:
        contents = []
        for item in messages:
            role = "user" if item["role"] == "user" else "model"
            contents.append(
                self._types.Content(
                    role=role,
                    parts=[self._types.Part(text=item["content"])],
                )
            )
        response = self._client.models.generate_content(
            model=model,
            contents=contents,
            config=self._types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=0.7,
            ),
        )
        text = (response.text or "").strip()
        if not text:
            raise RuntimeError("Gemini returned an empty response")
        return text


def resolve_backend(api_key: str | None) -> LlmBackend:
    key = (api_key or "").strip()
    if not key:
        return EchoLlm()
    return GeminiLlm(api_key=key)


def backend_status(api_key: str | None) -> tuple[Literal["gemini", "echo"], str]:
    backend = resolve_backend(api_key)
    return backend.name, backend.model  # type: ignore[return-value]
