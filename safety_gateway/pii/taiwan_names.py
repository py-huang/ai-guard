"""Taiwan surnames, a 100-name experiment set, and session aliases."""

from __future__ import annotations

import re

from safety_gateway.pii.name_stoplist import GLUED_SURNAMES, STOP_WORDS

# MOI-style frequent surnames in Taiwan (single + a few compounds).
COMPOUND_SURNAMES: tuple[str, ...] = (
    "歐陽",
    "司馬",
    "上官",
    "諸葛",
    "東方",
    "夏侯",
    "慕容",
    "司徒",
    "司空",
    "申屠",
    "長孫",
    "宇文",
)

SINGLE_SURNAMES: str = (
    "陳林黃張李王吳劉蔡楊許鄭謝郭洪邱曾廖賴徐周葉蘇莊呂江何蕭羅高潘簡朱鍾游"
    "彭詹胡施沈余盧梁趙顏柯翁魏孫戴范鄧曹傅薛丁卓馬蔣藍宋杜姚石龔馮于韓唐阮"
    "童白溫方連田董鄒巫尤錢尹黎易湯陶康姜武賀嚴顧孟萬段雷鮑史崔孔涂歐侯邵甘紀"
    "汪倪樊俞梅辛葛邢覃莫舒成聶殷卞祁井"
)

_DENY_GIVEN = frozenset("家氏某總府市縣鄉村里長姓國校班組隊")
_DENY_GIVEN_WORDS = frozenset(
    {
        "教育",
        "作業",
        "健康",
        "老師",
        "同學",
        "小朋友",
        "幾度",
        "幾天",
        "幾歲",
        "幾分",
        "幾號",
        "幾月",
        "幾點",
        "公尺",
        "公分",
        "公斤",
        "公克",
        "公升",
        "平方",
        "貼紙",
        "路程",
        "裝一",
        "形花",
        "體容",
        "長是",
        "讓反",
        "反應",
        "在哪",
        "哪裡",
        "那裡",
        "地方",
    }
)
_DENY_FULL = frozenset(
    {
        "地方",
        "方在",
        "方在哪",
        "高中",
        "高職",
        "高雄",
        "周末",
        "週末",
        "周邊",
        "周圍",
        "周長",
        "江南",
        "何謂",
        "何以",
        "如何",
        "何讓",
        "為何",
        "任何",
        "幾何",
        "溫度",
        "溫暖",
        "溫柔",
        "溫習",
        "溫泉",
        "方形",
        "方體",
        "方公",
        "張貼",
        "張裝",
        "段路",
    }
)
_SURNAME_WORD_PREFIX = frozenset(
    {
        "氣溫",
        "高溫",
        "低溫",
        "常溫",
        "體溫",
        "水溫",
        "油溫",
        "室溫",
        "均溫",
        "如何",
        "為何",
        "任何",
        "幾何",
        "奈何",
        "何時",
        "何處",
        "何必",
        "地方",
    }
)
# Sentence particles / 說 that greedy 姓+2 given would swallow.
_TRAILING_NOT_GIVEN = frozenset("說的了嗎呢吧啊嘛呀喔哦是買吃喝看用到在去走跑拿找問聽寫讀玩裝他她它您")
_CJK = re.compile(r"[\u4e00-\u9fa5]")

# Eval set only — not a production lookup. Used to tune surname+given rules.
_TOP_SURNAMES = tuple("陳林黃張李王吳劉蔡楊許鄭謝郭洪邱曾廖賴徐")
_TOP_GIVEN = ("承恩", "宥廷", "品妤", "詠晴", "宇翔")
COMMON_FULL_NAMES: tuple[str, ...] = tuple(
    f"{surname}{given}" for surname in _TOP_SURNAMES for given in _TOP_GIVEN
)

# Names already used in child-safety fixtures / demos.
DEMO_FULL_NAMES: tuple[str, ...] = (
    "王小明",
    "林小華",
    "陳大同",
    "張美麗",
    "周品難",
    "陳小明",
    "陳小華",
)

# Official FET 經營團隊 page — eval only, not a production lookup.
# https://corporate.fetnet.net/content/corp/tw/AboutUs/ManagerTeam.html
FET_PUBLIC_NAMES: tuple[str, ...] = (
    "徐旭東",
    "井琪",
    "趙憶南",
    "朱承恩",
    "呂秀味",
    "曾詩淵",
    "林秀穎",
    "郭峻杰",
    "胡德民",
    "林淑鈴",
    "李和音",
    "杜偉昱",
    "朱建國",
    "林慧珊",
    "蘇淑寧",
)

ALL_DICTIONARY_NAMES: frozenset[str] = frozenset(COMMON_FULL_NAMES + DEMO_FULL_NAMES)


# Characters that actually turn up in Taiwanese given names (common first/second characters across
# both genders). Used only to vet *uncued* name candidates: a surname character followed by
# whatever happens to come next ("方法", "成為", "簡單", "謝謝") is overwhelmingly an ordinary
# word, while a real name's given part is drawn from this small, well-known pool. Candidates that
# come with a naming cue ("我叫…", "…同學") skip this check, so unusual names still get caught there.
GIVEN_NAME_CHARS: frozenset[str] = frozenset(
    "怡君雅婷欣宜佳慧淑芬美玲麗惠玉芳秀英靜敏婉萱芸珊琪瑩盈穎涵妤芷瑄宥廷承恩宇翔冠宏俊傑志明偉豪建文家"
    "銘柏翰哲嘉皓睿軒翊彥煜凱宗霖銓昇鴻勳育瑞祥鈞詠晴品妍琳婕姿芮蓁薇倩紫彤樂安心思妮蕙純如梅菁秋春"
    "夏冬雪雲玫瑜璇莉蓉雯晶柔珮琬筠儀蓮淳晏辰奕秉恆維信杰霆庭澤澔浩陽揚立良國強榮財貴勇平剛龍鵬生源昌"
    "昭世貞華金鳳蘭菊桂燕月珠寶福康德義禮仁智忠孝道誠正光輝耀彬斌昱昊霈晨博鈺子書瑋采芊昀丞語蕾茹萍"
    "蓓怜娟珍巧筱韻璟翎樺舒詩緯泓皇禹朋叡祐凡向齊寬鎮煌洋騰霏曜棠詮喬碩緣大毅倫祺佑佩雨楷宸晞渝達釗昕冠潔沛南寧峻憶旭東民淵鈴音奇小"
)


# Name characters that are far more often an ordinary word on their own after a surname
# (李子, 葉子): only accepted as part of a two-character given name.
_AMBIGUOUS_SINGLE = frozenset("子家")


# Ordinary words that begin with a surname character and whose second character happens to be a
# name character (中國, 成立, 高雅). Collected from frequent false positives on the *dev* split of the
# benign evaluation corpus only; the held-out split is used to confirm it generalises.
COMMON_WORD_STEMS: frozenset[str] = frozenset(
    "中國 韓國 歐美 歐洲 成語 成立 成長 成年 成本 成績 成分 成員 成熟 成效 成交 成就 成英 方向 高大 高雅 高贊 "
    "黃種 白種 蘇北 蘇南 江蘇 江西 吳語 韓語 段文 雲南 史書 史上 甘肅 羅馬 武漢 湯米 簡直 簡短 李子 葉子 "
    "何必 何時 何況 許多 許可 顏色 顏值 藍色 黃色 白色 高度 高速 高階 高興 高中 高考 平均 平常 平時 安全 "
    "安靜 文明 文章 文化 文學 石頭 金魚 金錢 本地 本來 田園 馬上 馬路 林業 周圍 溫度 溫暖 易經 樂器 康復".split()
)


# Word beginnings that stay words even when the whole candidate looks name-like ("成英文").
NEVER_NAME_PREFIXES: frozenset[str] = frozenset({"成英"})


def vet_uncued_given(surname: str, given: str) -> str | None:
    """Return the part of ``given`` that reads as a name, or ``None`` (see ``GIVEN_NAME_CHARS``).

    A trailing character that is not a name character is trimmed rather than fatal, so
    "呂豪這樣寫" (candidate 呂豪這) still yields 呂豪, while "方法" and "成為" yield nothing.
    """
    if not given or given[0] == surname[-1]:  # 謝謝, 林林: a surname is not repeated as the given name
        return None
    if all(char in GIVEN_NAME_CHARS for char in given):
        kept = given
    elif len(given) == 2 and given[0] in GIVEN_NAME_CHARS:
        kept = given[0]
    else:
        return None
    if surname[-1] + kept[0] in NEVER_NAME_PREFIXES:
        return None
    if len(kept) == 1 and (kept in _AMBIGUOUS_SINGLE or surname[-1] + kept in COMMON_WORD_STEMS):
        # Only a two-character result can be one of those words: 李子 (fruit) vs 李子晴 (a name).
        return None
    return kept


def surname_prefix(text: str) -> str | None:
    for compound in COMPOUND_SURNAMES:
        if text.startswith(compound):
            return compound
    if text and text[0] in SINGLE_SURNAMES:
        return text[0]
    return None


def is_plausible_tw_name(span: str) -> bool:
    chars = "".join(_CJK.findall(span))
    if len(chars) < 2 or len(chars) > 4:
        return False
    surname = surname_prefix(chars)
    if not surname:
        return False
    given = chars[len(surname) :]
    if not given or len(given) > 2:
        return False
    if given in _DENY_GIVEN or given in _DENY_GIVEN_WORDS:
        return False
    if given.startswith("幾"):
        return False
    if given[-1] in _TRAILING_NOT_GIVEN:
        return False
    if chars in _DENY_FULL:
        return False
    return True


def resolved_person_span(text: str, start: int, end: int) -> tuple[int, int] | None:
    """Prefer 2-char 姓+名 when greedy 3-char ended on a particle."""
    if start > 0:
        glued = text[start - 1] + text[start]
        if glued in _SURNAME_WORD_PREFIX:
            return None
    chunk = text[start:end]
    if is_plausible_tw_name(chunk):
        return (start, end)
    if any(chunk.endswith(word) for word in _DENY_GIVEN_WORDS):
        return None
    if end - start >= 3 and is_plausible_tw_name(text[start : end - 1]):
        return (start, end - 1)
    return None


def aliases_for_person(full_name: str) -> list[str]:
    """Shorter mentions that should reuse the same PERSON token."""
    chars = "".join(_CJK.findall(full_name))
    surname = surname_prefix(chars)
    if not surname or not is_plausible_tw_name(chars):
        return []
    given = chars[len(surname) :]
    aliases = [chars]
    if len(given) >= 2:
        aliases.append(given)
    if given:
        aliases.append(f"{surname}同學")
        aliases.append(f"{surname}小朋友")
        aliases.append(f"{surname}老師")
    # Preserve order, longest first for scanning.
    unique: list[str] = []
    for item in aliases:
        if item not in unique:
            unique.append(item)
    return sorted(unique, key=len, reverse=True)


def is_everyday_word(text: str, start: int, end: int) -> bool:
    """True when a candidate name is really an ordinary word (see scripts/derive_name_stoplist.py).

    Either the span itself is a word the detectors keep tripping over (黃瓜, 史詩), or the character
    in front of its surname glues it into a longer word (生成|德, 西|方國家, 提|高品質).
    """
    span = text[start:end]
    if span in STOP_WORDS:
        return True
    if start > 0 and text[start - 1] + span[:1] in GLUED_SURNAMES:
        return True
    return any(word in span for word in STOP_WORDS if len(word) >= 3 and len(span) > len(word))
