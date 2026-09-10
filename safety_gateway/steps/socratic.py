"""Socratic pedagogy: scaffold homework dumps instead of handing over answers."""

from __future__ import annotations

from typing import ClassVar, Literal

from safety_gateway.steps.base import BaseGuardStep, GuardContext

HintLevel = Literal["gentle", "medium", "strict"]

HOMEWORK_CUES = (
    "作業",
    "功課",
    "答案",
    "幫我寫",
    "直接告訴我",
    "直接給我",
    "完整解答",
    "標準答案",
    "計算題",
    "改作文",
    "怎麼寫",
    "幫我算",
    "寫日記",
)

INBOUND_PREFIX = (
    "【教學模式】小朋友想直接拿到答案。請用蘇格拉底法："
    "先給一個小提示，最多示範一步，最後用一個問題請他自己想。"
    "不要一次寫完整解答。\n\n小朋友說："
)

OUTBOUND_HINTS: dict[HintLevel, str] = {
    "gentle": "\n\n你先試試看：這一步你會先做什麼？",
    "medium": "\n\n先別急著看完整答案。你覺得第一步該從哪裡開始？",
    "strict": "\n\n我只給提示：把題目拆成更小的一步，你會先寫哪一行？",
}


class SocraticPedagogyStep(BaseGuardStep):
    """Independent tutoring policy: wrap inbound dumps, require a guiding question outbound."""

    name: ClassVar[str] = "socratic_pedagogy"

    def __init__(
        self,
        hint_level: HintLevel = "gentle",
        cues: tuple[str, ...] = HOMEWORK_CUES,
        enabled: bool = True,
    ) -> None:
        self.hint_level = hint_level
        self._cues = cues
        self._enabled = enabled
        self._homework_sessions: dict[str, bool] = {}

    def looks_like_answer_dump(self, text: str) -> bool:
        return any(cue in text for cue in self._cues)

    def process_inbound(self, context: GuardContext) -> GuardContext:
        if context.blocked or not self._enabled:
            context.mark_step(self.name)
            return context
        if self.looks_like_answer_dump(context.text):
            self._homework_sessions[context.session_id] = True
            context.metadata["socratic_mode"] = True
            if not context.text.startswith("【教學模式】"):
                context.text = INBOUND_PREFIX + context.text
        else:
            context.metadata["socratic_mode"] = False
        context.mark_step(self.name)
        return context

    def process_outbound(self, context: GuardContext) -> GuardContext:
        if context.blocked or not self._enabled:
            context.mark_step(self.name)
            return context
        if self._homework_sessions.get(context.session_id) and not _has_guiding_question(
            context.text
        ):
            context.text = context.text.rstrip() + OUTBOUND_HINTS[self.hint_level]
            context.metadata["socratic_appended"] = True
        context.mark_step(self.name)
        return context


def _has_guiding_question(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if any(mark in stripped for mark in ("？", "?", "嗎？", "嗎?")):
        return True
    return stripped.endswith("嗎") or stripped.endswith("呢")
