"""K-12 content moderation aligned with Taiwan child-protection / rating categories."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import ClassVar, Mapping

from safety_gateway.steps.base import BaseGuardStep, GuardContext
from safety_gateway.steps.content_model import ContentModel

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
    "image_abuse": (
        "不可以拿別人的照片去改圖，或想像不適當的畫面。請尊重同學。"
        "如果只是想聊天，我們可以改談功課或今天發生的好事。"
    ),
    "grooming": (
        "如果有人要你保密、要單獨見面，或想知道你住哪裡、怎麼聯絡你，"
        "請馬上告訴爸爸媽媽或老師。你不會被罵，這樣做是對的。"
    ),
    "prompt_injection": (
        "這個要求我沒辦法做喔。我們回到你想學的事情，一起想想看吧！"
    ),
    "illegal": (
        "這個問題不適合在這裡討論。我們不能提供騙人、偷東西或違法的做法。"
        "如果你遇到被欺負或被騙的事，請告訴爸爸媽媽或老師。"
    ),
}

# High-recall catalog: short slang is included. Bare 「性」/「戰爭」still omitted
# so 性教育 / 二次大戰 homework is not blocked.
DEFAULT_CATALOG: dict[str, tuple[str, ...]] = {
    "sexual": (
        "色情",
        "做愛",
        "性交",
        "裸照",
        "裸體",
        "色情影片",
        "成人影片",
        "約砲",
        "約炮",
        "色情網站",
        "A片",
        "a片",
        "黃片",
        "18禁",
        "性行為",
        "裸聊",
        "兒童色情",
        "露點照",
        "裸露下體",
        "性侵",
        "性侵別人",
        "強姦",
        "強制性交",
        "性虐待",
        "性剝削",
        "援交",
        "自慰",
        "雞雞",
        "出軌",
        "口交",
        "射精",
        "陰莖",
        "陰道",
        "乳頭",
    ),
    "self_harm": (
        "自殺",
        "自殺方法",
        "怎麼自殺",
        "如何自殺",
        "我想死",
        "不想活",
        "不想活了",
        "割腕",
        "結束生命",
        "自我了結",
        "吞藥自殺",
        "上吊",
        "自殘",
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
        "殺人",
        "怎麼殺人",
        "如何殺人",
        "殺了同學",
        "殺了老師",
        "炸彈",
        "製作炸彈",
        "炸彈做法",
        "怎麼做炸彈",
        "買槍殺",
        "傷害同學的方法",
        "校園槍擊",
        "槍擊",
        "砍人",
        "怎麼砍人",
        "虐殺",
        "虐殺動物",
        "虐待動物的方法",
        "開膛教學",
        "私刑燒死",
        "斷肢影片做法",
        "暴力",
    ),
    "horror": (
        "恐怖分屍",
        "碎屍",
        "碎屍影片",
        "想看食人",
        "食屍",
        "食屍影片",
        "嚇死同學的方法",
        "做跳嚇整同學",
        "超血腥屍體特寫",
        "血腥",
    ),
    "substance": (
        "吸毒",
        "教我吸毒",
        "毒品",
        "哪裡買毒品",
        "怎麼買毒品",
        "海洛因",
        "吸海洛因",
        "大麻",
        "吸大麻",
        "種大麻",
        "搖頭丸",
        "買搖頭丸",
        "請同學抽電子煙",
        "請小朋友抽菸",
        "請小朋友喝酒",
        "灌醉同學",
        "嚼檳榔比較神",
        "請未成年嚼檳榔",
    ),
    "hate_speech": (
        "幹你",
        "幹你娘",
        "幹你老師",
        "機掰",
        "智障",
        "去死",
        "去死啦智障",
        "身心障礙都該死",
        "外國人滾出台灣",
        "外籍移工滾",
        "去死吧障礙",
        "諷刺的話"
    ),
    "gambling": (
        "賭博",
        "線上娛樂城儲值",
        "真錢賭博",
        "教我賭球",
        "用零用錢下注",
        "娛樂城",
        "娛樂城儲值",
        "簽賭",
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
    "image_abuse": (
        "上廁所的照片",
        "在廁所的照片",
        "廁所照",
        "上廁所照",
        "換衣服的照片",
        "在換衣服的照片",
        "脫衣服的照片",
        "洗澡的照片",
        "在洗澡的照片",
        "廁所自拍",
        "換衣服自拍",
        "畫他上廁所",
        "畫她上廁所",
        "畫這個人上廁所",
        "生成上廁所",
        "p成上廁所",
        "畫一個小朋友",
        "畫一個小孩",
        "畫同學的臉",
        "畫人像",
        "生成人像",
        "畫一張臉",
        "畫一個男生",
        "畫一個女生",
    ),
    # Someone asking a child to keep secrets, meet alone, or move to a private channel.
    "grooming": (
        "不要告訴爸媽",
        "不要告訴爸爸媽媽",
        "別告訴爸媽",
        "不要跟爸媽說",
        "不要讓爸媽知道",
        "不要讓老師知道",
        "不要告訴老師",
        "不要告訴任何人",
        "私下聯絡",
        "私下見面",
        "單獨見面",
        "加我私聊",
        "私聊我",
        "加我line",
        "加我賴",
        "加我ig",
    ),
    # Attempts to rewrite the assistant's rules or extract its hidden instructions.
    "prompt_injection": (
        "忽略之前的指令",
        "忽略之前所有",
        "忽略以上指令",
        "忽略上面的指令",
        "忽略所有指令",
        "忽略你的指令",
        "忽略你的規則",
        "無視之前的指令",
        "無視你的規則",
        "忘記你的規則",
        "忘掉你的規則",
        "忘記之前的指令",
        "ignore previous instructions",
        "ignore all previous",
        "ignore the above",
        "ignore your instructions",
        "disregard your instructions",
        "system prompt",
        "系統提示詞",
        "你的提示詞",
        "印出你的指令",
        "你現在是dan",
        "dan模式",
        "jailbreak模式",
        "jailbreak mode",
        "越獄模式",
        "進入開發者模式",
        "developer mode enabled",
        "沒有限制的ai",
        "沒有安全規則",
    ),
}

# Extra phrases for categories above, kept separate so the base catalog stays readable.
_EXTRA_PHRASES: dict[str, tuple[str, ...]] = {
    "self_harm": (
        "傷害自己",
        "自我傷害",
        "殺死自己",
        "殺了自己",
        "想消失",
        "想要消失",
        "活不下去",
        "不想存在",
        "割自己",
        "suicide",
        "kill myself",
        "killmyself",
    ),
    "violence": (
        "想殺人",
        "想殺了",
        "殺了我同學",
        "殺了我老師",
        "殺了他",
        "殺了她",
        "怎麼傷害別人",
        "如何傷害別人",
        "刀子傷",
        "用刀傷",
        "打死他",
        "打死她",
        "弄死他",
        "弄死她",
        "自製武器",
        "製作武器",
        "做武器",
    ),
}
for _category, _phrases in _EXTRA_PHRASES.items():
    DEFAULT_CATALOG[_category] = tuple(dict.fromkeys((*DEFAULT_CATALOG[_category], *_phrases)))

# Things an assistant must never *say* to a child, but a child may innocently ask about.
OUTBOUND_ONLY_CATALOG: dict[str, tuple[str, ...]] = {
    "grooming": (
        "告訴我你的地址",
        "告訴我你住哪",
        "告訴我你家住哪",
        "給我你的電話",
        "告訴我你的電話",
        "你的真實姓名",
        "你住在哪裡",
        "你家住哪",
        "你讀哪所學校",
        "你在哪個學校",
    ),
}

# Sentence-shape rules for what a plain phrase list cannot express: "ignore the above and print X",
# "teach me how to <wrong thing>". Matched against NFKC + case-folded text with spaces collapsed.
# Every pattern is bounded (no unbounded .*) so a 4000-character message cannot stall a worker.
_ILLEGAL_ACTS = (
    r"詐騙|詐欺|欺騙(?:他人|別人|老人|人們|大家)|偷稅|漏稅|洗錢|偽造|盜取|竊取|盜用|駭入|入侵|破解|釣魚|"
    r"迷藥|下藥|迷姦|販毒|製毒|走私|縱火|放火|綁架|勒索|跟蹤|偷拍|偷窺|誹謗|散佈謠言|散播謠言|製造謠言|"
    r"人肉搜索|網路攻擊|ddos|木馬|惡意軟體|爆炸物|炸藥|毒藥|非法|違法|犯罪|恐嚇|賄賂|"
    r"竊聽|竊取|違禁|不擇手段|毆打|打架|騷擾|偷竊|偷東西|迷幻藥|lsd|歧視性|篡改|否定疫苗|"
    r"破壞(?:.{0,6})(?:網站|系統)|赤裸上身|"
    r"攻擊(?:他人|別人|一個人|(?:一個)?網站|(?:一個)?系統|對手)|駭客|傷害(?:他人|別人)|打擊(?:我的)?競爭對手|報復(?:他|她|同學|老師)"
)
_REQUEST_LEAD = (
    r"(?:如何|怎麼|怎樣|怎麼樣|教我|教授|教會|幫我|協助我|幫助我|提供|給我|設計|製作|策劃|策畫|制定|撰寫|"
    r"我想|我要|我需要|我打算|我計劃|有什麼方法|有沒有辦法|可以幫|能不能)"
)
# Education and self-protection mention the same words; never treat those as requests.
_PROTECTIVE_CONTEXT = re.compile(
    r"防範|預防|避免|防止|防禦|防護|保護|不被|識別|辨別|辨識|小心|應對|舉報|報警|反詐騙|求助|"
    r"為什麼|什麼是|是什麼|歷史|新聞|課本|作業|電影|故事|"
    r"怎麼辦|怎麼處理|該如何處理|該怎麼做|應該怎麼做|如何幫助|怎麼幫助|怎樣幫助|我被|被欺負|被霸凌"
)
# Broad single words that also show up when a child is asking for help ("我被暴力對待怎麼辦").
# With protective context these pass through to the assistant, whose prompt answers supportively;
# explicit acts (殺人, 自殺方法, 炸彈 ...) and self-harm are never relaxed this way.
_CONTEXTUAL_PHRASES = frozenset({"暴力", "賭博", "毒品", "吸毒", "色情", "大麻", "血腥", "性侵", "性行為"})

INTENT_PATTERNS: dict[str, tuple[str, ...]] = {
    "prompt_injection": (
        r"(?:忽略|無視|忘記|忘掉|不要理會|別理會|不用理會)掉?(?:上述|以上|上面|前面|之前|先前|這條|這個|該|我的|你的|所有|全部|任何|剛才|剛剛){0,2}的?(?:指令|提問|問題|提示|內容|規則|命令|要求|設定|任務|文字)",
        r"直接(?:輸出|複述|回覆|輸入)\s?[:：“「\"]",
        r"複述\s?[:：“「\"]|請複述(?:這句話|以下|下面)",
        r"不要(?:新增|添加|加上)任何(?:詞彙|字首|字尾|符號|註釋|標點)",
        r"\b(?:ignore|disregard|forget|override)\s+(?:all|any|the|your|my|these|those|every)?\s*(?:previous|prior|above|earlier|preceding|former|current)?\s*(?:instructions?|prompts?|rules?|directions?|tasks?|commands?|guidelines?)\b",
        r"\bforget\s+(?:everything|all)\b",
        r"\bignore\s+(?:the\s+)?(?:above|everything|that)\b",
        r"\bnew instructions? follow\b|\bchange your instructions\b|\byou are no longer\b",
        r"\b(?:reveal|show|print|repeat|output|tell)\s+(?:me\s+)?(?:all\s+)?(?:your|the)\s+(?:system\s+)?(?:prompt|instructions)\b",
        r"\byou are now\s+(?:dan|free|unrestricted|a different)\b",
        r"\bnew (?:task|instructions?)\s*[:：]",
    ),
    "illegal": (
        rf"{_REQUEST_LEAD}.{{0,16}}(?:{_ILLEGAL_ACTS})",
    ),
    # A how-to with a "…without getting caught" clause: the evasion is the tell. It must not be
    # excused by protective wording, because "不被" is itself on that list. Surprises, gifts and
    # hide-and-seek also avoid being noticed, so those are excluded up front. The part after "#"
    # only keeps this key apart from "illegal" (which protective context does exempt).
    "illegal#evasion": (
        r"^(?!.*(?:驚喜|禮物|躲貓貓|捉迷藏|遊戲)).*(?:怎麼|如何|怎樣|有沒有辦法|有什麼辦法|有辦法|教我|告訴我|幫我|請問).{0,24}"
        r"(?:而不被|又不被|才不會被|而不會被|不會被|不被|不要被).{0,3}(?:發現|抓到|抓住|查到|查出|識破|看到|拍到|逮到)",
    ),
    "hate_speech": (
        r"賤人|賤貨|賤種|下賤|犯賤|賤樣|賤狗|婊子|綠茶婊|聖母婊|母狗|傻逼|傻b|沙小|腦殘|蠢貨|混蛋|王八蛋|"
        r"他媽的|你媽的|幹你媽|操你媽|肏|狗娘養|狗東西|畜生|去你的|滾蛋|吃屎|低能兒|廢物(?!利用|處理|回收|再利用|桶)|"
        r"人渣|我操|操你|屁精|狗日|妓女|肥豬|\btmd\b|\btm的|\bnmsl\b|\bsb\b|\bwdnmd\b",
    ),
    "self_harm": (
        r"(?:我想|我要|想要|好想).{0,6}(?:跳樓|跳河|跳海|輕生|尋死)",
        r"(?:割|劃|割開).{0,3}(?:手腕|手臂|血管|自己)",
        r"(?:想|要|好想|想要).{0,10}(?:離開|告別).{0,4}(?:這個世界|人世)",
        r"(?:吞|吃|喝).{0,6}(?:安眠藥|藥).{0,8}(?:永遠睡著|自殺|不要醒|死掉)",
    ),
    # A child being asked for photos or secrecy: the shape matters, "不要讓媽媽知道" alone does not
    # (it is also a birthday surprise), so secrecy only counts next to photos, bodies or meeting.
    "grooming": (
        r"(?:給|傳|寄|拍|看).{0,6}(?:裸照|裸體|身體的照片|私密照)",
        r"(?:照片|身體|裸|私密|單獨|見面|約出來).{0,14}(?:不能|不要|別|不可以|不准).{0,3}(?:讓|給|被|告訴).{0,3}(?:別人|其他人|爸媽|父母|老師|大人|家人)",
        r"(?:不能|不要|別|不可以|不准).{0,3}(?:讓|給|被|告訴).{0,3}(?:別人|其他人|爸媽|父母|老師|大人|家人).{0,8}(?:知道|說).{0,14}(?:照片|身體|裸|私密|單獨|見面|約)",
    ),
}
# Categories whose patterns must be skipped when the message is clearly protective/educational.
_PROTECTIVE_EXEMPT = frozenset({"illegal"})

# Spacing, zero-width characters and punctuation are the cheapest way to dodge a phrase list
# ("怎麼自 殺", "s.u.i.c.i.d.e"), so matching runs on text with all of them removed.
_NOISE = re.compile(
    r"[\s\u00ad\u200b-\u200f\u2060\ufeff.,!?;:'\"`~*_|/\\()\[\]{}<>\-—–、。，！？；：「」『』（）…·・]+"
)


_SPACES = re.compile(r"\s+")


def fold(text: str) -> str:
    """Normalize for matching: NFKC, case-fold, drop spacing/punctuation noise."""
    return _NOISE.sub("", unicodedata.normalize("NFKC", text).casefold())

# Only when a face was found on an attached photo: refuse likeness edit / generation.
# Bare 「這張照片」or「上廁所」are omitted so homework and identity questions can pass.
IMAGE_ABUSE_WITH_FACE: tuple[str, ...] = (
    "p圖",
    "p成",
    "換臉",
    "deepfake",
    "生成這個人",
    "畫出這個人",
    "畫這個人",
    "這個人的照片",
    "修這張照片",
    "改這張照片",
    "用這張照片生成",
    "用這張照片畫",
    "把這張照片變成",
    "把這個人變成",
    "讓他脫",
    "讓她脫",
    "讓這個人脫",
    "讓他上廁所",
    "讓她上廁所",
    "讓這個人上廁所",
)

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


# Help-seeking about abuse ("同學罵我笨，怎麼辦") quotes the abuse; that is not abuse.
_MODEL_PROTECTIVE_EXEMPT = frozenset({"toxic", "unsafe"})


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
        model: ContentModel | None = None,
    ) -> None:
        # Optional trained classifier, consulted only when no phrase rule matched (see classify).
        self._model = model
        self._catalog = {
            category: tuple(phrases)
            for category, phrases in (catalog or DEFAULT_CATALOG).items()
        }
        self._messages = dict(child_messages or CHILD_MESSAGES)
        self._enabled = enabled
        self._folded = {
            category: tuple((phrase, fold(phrase)) for phrase in phrases if fold(phrase))
            for category, phrases in self._catalog.items()
        }
        # A custom catalog means the caller owns the whole policy; only defaults get extras.
        self._intent = (
            {c: tuple(re.compile(p) for p in ps) for c, ps in INTENT_PATTERNS.items()}
            if catalog is None
            else {}
        )
        outbound = OUTBOUND_ONLY_CATALOG if catalog is None else {}
        self._outbound_folded = {
            category: tuple((phrase, fold(phrase)) for phrase in phrases)
            for category, phrases in outbound.items()
        }

    @property
    def has_model(self) -> bool:
        return self._model is not None

    def process_inbound(self, context: GuardContext) -> GuardContext:
        self._apply(context)
        context.mark_step(self.name)
        return context

    def process_outbound(self, context: GuardContext) -> GuardContext:
        self._apply(context, outbound=True)
        context.mark_step(self.name)
        return context

    def classify(
        self, text: str, *, faces_detected: int = 0, outbound: bool = False
    ) -> SafetyMatch | None:
        if not self._enabled or not text or text == "[BLOCKED]":
            return None
        haystack = fold(text)
        normalized = _SPACES.sub(" ", unicodedata.normalize("NFKC", text).casefold())
        protective = bool(_PROTECTIVE_CONTEXT.search(normalized))
        tables = [self._folded]
        if outbound:
            tables.append(self._outbound_folded)
        for table in tables:
            for category, phrases in table.items():
                for phrase, folded in phrases:
                    if folded not in haystack:
                        continue
                    if protective and not outbound and phrase in _CONTEXTUAL_PHRASES:
                        continue
                    return SafetyMatch(category=category, phrase=phrase)
        if self._intent:
            for key, patterns in self._intent.items():
                if protective and key in _PROTECTIVE_EXEMPT:
                    continue
                category = key.split("#")[0]
                for pattern in patterns:
                    found = pattern.search(normalized)
                    if found:
                        return SafetyMatch(category=category, phrase=f"~{found.group(0)[:24]}")
        if faces_detected > 0:
            for phrase in IMAGE_ABUSE_WITH_FACE:
                if fold(phrase) in haystack:
                    return SafetyMatch(category="image_abuse", phrase=phrase)
        if self._model is not None and not outbound:
            # The model reads short child messages; model replies are moderated by rules only.
            verdict = self._model.predict(text)
            if verdict.blocked and not (protective and verdict.label in _MODEL_PROTECTIVE_EXEMPT):
                return SafetyMatch(
                    category=verdict.category or "illegal",
                    phrase=f"ml:{verdict.label}:{verdict.block_score:.2f}",
                )
        return None

    def _apply(self, context: GuardContext, *, outbound: bool = False) -> None:
        if context.blocked:
            return
        faces = int(context.metadata.get("faces_detected") or 0)
        match = self.classify(context.text, faces_detected=faces, outbound=outbound)
        context.metadata["homework_context"] = any(item in context.text for item in HOMEWORK_ALLOWLIST)
        if match is None:
            context.metadata["content_safety"] = "allow"
            return
        message = self._messages.get(match.category, CHILD_MESSAGES["violence"])
        context.block(match.category, message)
        context.metadata["content_safety"] = "block"
        context.metadata["content_safety_phrase"] = match.phrase
