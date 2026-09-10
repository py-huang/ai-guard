"""K-12 content moderation aligned with Taiwan child-protection / rating categories."""

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
    "horror": (
        "太驚嚇、太血腥的畫面不適合在這裡看。"
        "我們可以改聊功課，或你喜歡的故事。"
    ),
    "substance": (
        "菸、酒、檳榔和毒品都不適合兒童。"
        "如果是健康教育想問危害，可以問老師或看課本，不要自己試。"
    ),
    "hate_speech": (
        "這樣的話會傷害別人。我們用尊重的方式和同學相處。"
        "想聊天的話，可以改談功課或今天發生的好事。"
    ),
    "gambling": (
        "用真錢賭博或簽賭不適合兒童。"
        "如果是數學課的機率問題，我們可以用課本上的例子一起想。"
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
        "兒童色情",
        "露點照",
        "裸露下體",
        "性侵別人",
        "強姦",
        "強制性交",
        "性虐待",
        "性剝削",
        "援交",
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
        "自殘方法",
        "自殘教學",
        "割腕教學",
        "窒息挑戰",
        "從頂樓跳",
        "從屋頂跳",
        "燒炭自殺",
        "挑戰喝漂白水",
        "喝農藥",
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
        "怎麼砍人",
        "虐殺動物",
        "虐待動物的方法",
        "開膛教學",
        "私刑燒死",
        "斷肢影片做法",
    ),
    "horror": (
        "恐怖分屍",
        "碎屍影片",
        "想看食人",
        "食屍影片",
        "嚇死同學的方法",
        "做跳嚇整同學",
        "超血腥屍體特寫",
    ),
    "substance": (
        "教我吸毒",
        "哪裡買毒品",
        "怎麼買毒品",
        "吸海洛因",
        "吸大麻",
        "種大麻",
        "買搖頭丸",
        "請同學抽電子煙",
        "請小朋友抽菸",
        "請小朋友喝酒",
        "灌醉同學",
        "嚼檳榔比較神",
        "請未成年嚼檳榔",
    ),
    "hate_speech": (
        "幹你娘",
        "幹你老師",
        "機掰",
        "去死啦智障",
        "身心障礙都該死",
        "外國人滾出台灣",
        "外籍移工滾",
        "去死吧障礙",
    ),
    "gambling": (
        "線上娛樂城儲值",
        "真錢賭博",
        "教我賭球",
        "用零用錢下注",
        "娛樂城儲值",
        "簽賭網站",
        "玩真錢撲克",
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
    "菸害防制",
    "反毒",
    "人權作業",
    "法律作業",
    "電影分級",
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
