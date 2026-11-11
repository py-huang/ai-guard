"""Synthetic Taiwanese PII with realistic noise, for measuring recall at a scale that
hand-written examples cannot reach.

Deliberately independent of the recognizers: names, formats and noise are generated from
pools defined here, never imported from ``safety_gateway.pii`` (except the ID checksum, which is
a published standard), so a recognizer cannot score well merely by mirroring its own test data.

Every sample is (kind, noise, text, secrets). A sample is *protected* when none of its
``secrets`` survive in the gateway's processed text. Kinds are the things a child can reveal.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from safety_gateway.pii.checksum import is_valid_tw_national_id

_SURNAMES = "陳林黃張李王吳劉蔡楊許鄭謝郭洪邱曾廖賴徐周葉蘇莊呂江何蕭羅高潘簡朱鍾彭詹胡施"
_GIVEN = (
    "承恩宥廷品妤詠晴宇翔冠宇雅婷怡君佳穎俊宏柏翰子萱欣妍家豪建志思穎心怡鈺婷"
    "雅雯博文淑芬靜宜志明美玲偉倫宗翰書瑋芷瑄采妮奕辰芊語昱丞昀珊"
)
_CITIES = ("台北市", "新北市", "桃園市", "台中市", "台南市", "高雄市", "新竹市", "基隆市", "嘉義市")
_DISTRICTS = ("中山區", "大安區", "信義區", "北區", "東區", "西屯區", "三民區", "板橋區", "中正區", "永和區")
_ROADS = ("忠孝東路", "中山路", "光復路", "建國路", "民生路", "和平路", "文化路", "中華路", "仁愛路", "復興路")
_HANDLES = ("xiaoming", "happy_cat", "mei.lin", "kevin2015", "tony_wang", "amy0612", "little.star", "ming_ming")
_DOMAINS = ("gmail.com", "yahoo.com.tw", "hotmail.com", "outlook.com", "icloud.com")
_CN_DIGITS = "零一二三四五六七八九"
_FULL = str.maketrans("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
                      "０１２３４５６７８９ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ")

CARRIERS = (
    "我叫{X}，今年八歲。",
    "老師，我是{X}。",
    "我的名字是{X}，請問可以幫我寫作業嗎？",
    "你可以記住這個嗎：{X}",
    "{X} 這是我的，不要告訴別人",
    "幫我寫一封信，裡面要有{X}",
    "我媽媽說可以給你{X}",
    "聯絡我的方式是{X}喔",
    "我寫在本子上的是{X}，你看得到嗎",
    "請問{X}這樣寫對嗎？",
)

KINDS = ("name", "phone", "tw_id", "email", "address", "school", "line_id")


@dataclass(frozen=True)
class Sample:
    kind: str
    noise: str
    text: str
    secrets: tuple[str, ...]


def _digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


def _name(rng: random.Random) -> tuple[str, str]:
    given = "".join(rng.choice(_GIVEN) for _ in range(rng.choice((1, 2))))
    return rng.choice(_SURNAMES) + given, given


def _phone(rng: random.Random) -> tuple[str, str]:
    body = "09" + _digits(rng, 8)
    noise = rng.choice(("clean", "dashed", "spaced", "intl", "fullwidth", "dotted", "chinese", "zerowidth", "spoken_gaps"))
    a, b, c = body[:4], body[4:7], body[7:]
    if noise == "clean":
        return body, noise
    if noise == "dashed":
        return f"{a}-{b}-{c}", noise
    if noise == "spaced":
        return f"{a} {b} {c}", noise
    if noise == "intl":
        return f"+886 {body[1:4]} {b} {c}", noise
    if noise == "fullwidth":
        return body.translate(_FULL), noise
    if noise == "dotted":
        return f"{a}.{b}.{c}", noise
    if noise == "chinese":
        return "".join(_CN_DIGITS[int(d)] for d in body), noise
    if noise == "zerowidth":
        return f"{a}\u200b{b}\u200b{c}", noise
    return " ".join(body), noise  # one digit at a time, as dictated


def _tw_id(rng: random.Random) -> tuple[str, str]:
    letter = rng.choice("ABCDEFGHJKLMNPQRSTUVXYZ")
    head = letter + rng.choice("12") + _digits(rng, 7)
    value = next(head + d for d in "0123456789" if is_valid_tw_national_id(head + d))
    noise = rng.choice(("clean", "lower", "spaced", "dashed", "fullwidth"))
    if noise == "clean":
        return value, noise
    if noise == "lower":
        return value.lower(), noise
    if noise == "spaced":
        return f"{value[0]} {value[1:4]} {value[4:7]} {value[7:]}", noise
    if noise == "dashed":
        return f"{value[0]}-{value[1:]}", noise
    return value.translate(_FULL), noise


def _email(rng: random.Random) -> tuple[str, str]:
    handle = rng.choice(_HANDLES) + _digits(rng, rng.choice((0, 2, 3)))
    domain = rng.choice(_DOMAINS)
    noise = rng.choice(("clean", "at_dot", "fullwidth_at", "cn_at", "with_cue"))
    if noise == "at_dot":
        return f"{handle} at {domain.replace('.', ' dot ')}", noise
    if noise == "fullwidth_at":
        return f"{handle}＠{domain}", noise
    if noise == "cn_at":
        return f"{handle}小老鼠{domain.replace('.', '點')}", noise
    if noise == "with_cue":
        return f"我的信箱：{handle}@{domain}", noise
    return f"{handle}@{domain}", noise


def _address(rng: random.Random) -> tuple[str, str]:
    city, district, road = rng.choice(_CITIES), rng.choice(_DISTRICTS), rng.choice(_ROADS)
    number = rng.randint(1, 399)
    noise = rng.choice(("full", "no_city", "floor", "section"))
    if noise == "no_city":
        return f"{district}{road}{number}號", noise
    if noise == "floor":
        return f"{city}{district}{road}{number}號{rng.randint(2, 15)}樓", noise
    if noise == "section":
        return f"{city}{district}{road}{rng.randint(1, 5)}段{number}號", noise
    return f"{city}{district}{road}{number}號", noise


def _school(rng: random.Random) -> tuple[str, str]:
    place = rng.choice(("大安", "信義", "中山", "光復", "建國", "民生", "和平", "文化", "仁愛", "復興", "忠孝", "新生"))
    level = rng.choice(("國小", "國中", "國民小學", "國民中學"))
    noise = "plain"
    prefix = rng.choice(("", "", rng.choice(_CITIES[:5]) + "市立".replace("市市", "市")))
    if prefix:
        noise = "with_city"
    return f"{prefix}{place}{level}", noise


def _line(rng: random.Random) -> tuple[str, str]:
    handle = rng.choice(_HANDLES) + _digits(rng, rng.choice((2, 4)))
    cue = rng.choice(("LINE ID是", "line id：", "我的LINE ID是", "Line 帳號 "))
    return f"{cue}{handle}", "cue"


def generate(count_per_kind: int, seed: int = 20260511) -> list[Sample]:
    rng = random.Random(seed)
    samples: list[Sample] = []
    makers = {
        "name": _name, "phone": _phone, "tw_id": _tw_id, "email": _email,
        "address": _address, "school": _school, "line_id": _line,
    }
    for kind in KINDS:
        for _ in range(count_per_kind):
            carrier = rng.choice(CARRIERS)
            if kind == "name":
                full, given = _name(rng)
                samples.append(Sample(kind, "plain", carrier.format(X=full), (full, given)))
                continue
            surface, noise = makers[kind](rng)
            # What must NOT survive: the sensitive core, not the cue word we put in front of it.
            core = surface
            for cue in ("LINE ID是", "line id：", "我的LINE ID是", "Line 帳號 ", "我的信箱："):
                core = core.replace(cue, "")
            samples.append(Sample(kind, noise, carrier.format(X=surface), (core.strip(),)))
    return samples
