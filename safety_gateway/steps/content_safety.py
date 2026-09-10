"""K-12 content moderation: sexual, self-harm, and violence intent — not homework."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Mapping

from safety_gateway.steps.base import BaseGuardStep, GuardContext

CHILD_MESSAGES: dict[str, str] = {
    "sexual": (
        "這件事不適合在這裡討論。如果有人讓你不舒服，"
        "請立刻告訴爸爸媽媽或老師。我們可以改聊功課或今天發生的好事。"
    ),
    "self_harm": (
        "你很重要。如果現在很難過或害怕，請立刻告訴身邊的大人，"
        "或撥打 1925 安心專線。這裡不能討論傷害自己的方法，"
        "但可以陪你想怎麼尋求幫助。"
    ),
    "violence": (
        "這個問題不適合在這裡討論。我們不能提供傷害別人或危險的做法。"
        "要不要改聊功課、故事，或你今天想學的事情？"
    ),
    "bullying": (
        "不可以拿同學的照片來開玩笑或惡搞。請尊重同學。"
        "如果只是想聊天，我們可以改談功課或今天發生的好事。"
    ),
}

# Explicit instructional / help-seeking phrases. Short tokens like 「性」or「戰爭」
# are omitted so health-education and history homework are not blocked.
DEFAULT_CATALOG: dict[str, tuple[str, ...]] = {
    "sexual": (
        "色情",
        "做愛",
        "性交",
        "裸照",
        "色情影片",
        "成人影片",
        "約砲",
        "色情網站",
        "A片",
        "a片",
        "性行為",
        "裸聊",
    ),
    "self_harm": (
        "自殺方法",
        "怎麼自殺",
        "如何自殺",
        "我想死",
        "不想活了",
        "割腕",
        "結束生命",
        "自我了結",
        "吞藥自殺",
        "上吊",
    ),
    "violence": (
        "怎麼殺人",
        "如何殺人",
        "殺了同學",
        "殺了老師",
        "製作炸彈",
        "炸彈做法",
        "怎麼做炸彈",
        "買槍殺",
        "傷害同學的方法",
        "校園槍擊",
    ),
    "bullying": (
        "惡搞同學",
        "拿同學照片搞怪",
        "把同學P成",
        "P圖同學",
        "同學醜照",
        "醜化同學",
        "惡搞同學的照片",
        "把同學的臉P",
        "拿同學的照片開玩笑",
    ),
}

# If these appear, we still allow the turn unless an explicit catalog phrase also matches.
HOMEWORK_ALLOWLIST = (
    "歷史作業",
    "第二次世界大戰",
    "健康教育",
    "性教育",
    "生殖系統",
    "反霸凌",
    "交通安全",
)


@dataclass(frozen=True)
class SafetyMatch:
    category: str
    phrase: str


class ContentSafetyStep(BaseGuardStep):
    """Phrase classifier with an allowlist so homework is not over-blocked."""

    name: ClassVar[str] = "content_safety"

    def __init__(
        self,
        catalog: Mapping[str, tuple[str, ...]] | None = None,
        child_messages: Mapping[str, str] | None = None,
        enabled: bool = True,
    ) -> None:
        self._catalog = {
            category: tuple(phrases)
            for category, phrases in (catalog or DEFAULT_CATALOG).items()
        }
        self._messages = dict(child_messages or CHILD_MESSAGES)
        self._enabled = enabled

    def process_inbound(self, context: GuardContext) -> GuardContext:
        self._apply(context)
        context.mark_step(self.name)
        return context

    def process_outbound(self, context: GuardContext) -> GuardContext:
        self._apply(context)
        context.mark_step(self.name)
        return context

    def classify(self, text: str) -> SafetyMatch | None:
        if not self._enabled or not text or text == "[BLOCKED]":
            return None
        haystack = text.casefold()
        for category, phrases in self._catalog.items():
            for phrase in phrases:
                if phrase.casefold() in haystack:
                    return SafetyMatch(category=category, phrase=phrase)
        return None

    def _apply(self, context: GuardContext) -> None:
        if context.blocked:
            return
        match = self.classify(context.text)
        context.metadata["homework_context"] = any(item in context.text for item in HOMEWORK_ALLOWLIST)
        if match is None:
            context.metadata["content_safety"] = "allow"
            return
        message = self._messages.get(match.category, CHILD_MESSAGES["violence"])
        context.block(match.category, message)
        context.metadata["content_safety"] = "block"
        context.metadata["content_safety_phrase"] = match.phrase
