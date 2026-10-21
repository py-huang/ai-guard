"""Taiwan surnames, a 100-name experiment set, and session aliases."""

from __future__ import annotations

import re

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
