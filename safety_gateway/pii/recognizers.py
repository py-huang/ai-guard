"""Taiwan-localized Presidio recognizers (Traditional Chinese + local formats)."""

from __future__ import annotations

import re
from typing import ClassVar

from presidio_analyzer import (
    EntityRecognizer,
    Pattern,
    PatternRecognizer,
    RecognizerResult,
)
from presidio_analyzer.nlp_engine import NlpArtifacts

from safety_gateway.pii.checksum import is_valid_tw_national_id

_CJK = r"\u4e00-\u9fa5"
_ASCII_BOUND_LEFT = r"(?<![A-Za-z0-9])"
_ASCII_BOUND_RIGHT = r"(?![A-Za-z0-9])"


class TaiwanPhoneRecognizer(PatternRecognizer):
    """Mobile `09xxxxxxxx` / `09xx-xxx-xxx` and landlines with regional area codes."""

    PATTERNS: ClassVar[list[Pattern]] = [
        Pattern(
            name="tw_mobile_dashed",
            regex=rf"{_ASCII_BOUND_LEFT}09\d{{2}}-\d{{3}}-\d{{3}}{_ASCII_BOUND_RIGHT}",
            score=0.85,
        ),
        Pattern(
            name="tw_mobile_dashed_compact",
            regex=rf"{_ASCII_BOUND_LEFT}09\d{{2}}-\d{{6}}{_ASCII_BOUND_RIGHT}",
            score=0.7,
        ),
        Pattern(
            name="tw_mobile_plain",
            regex=rf"{_ASCII_BOUND_LEFT}09\d{{8}}{_ASCII_BOUND_RIGHT}",
            score=0.65,
        ),
        Pattern(
            name="tw_landline_02",
            regex=rf"{_ASCII_BOUND_LEFT}02-\d{{4}}-\d{{4}}{_ASCII_BOUND_RIGHT}",
            score=0.85,
        ),
        Pattern(
            name="tw_landline_zoned_dashed",
            regex=rf"{_ASCII_BOUND_LEFT}0(?:[3-8]|37|49|82|89)-\d{{3,4}}-\d{{3,4}}{_ASCII_BOUND_RIGHT}",
            score=0.8,
        ),
        Pattern(
            name="tw_landline_plain",
            regex=rf"{_ASCII_BOUND_LEFT}0(?:2\d{{8}}|[3-8]\d{{7,8}}|37\d{{6,7}}|49\d{{7}}|8[29]\d{{6,7}}){_ASCII_BOUND_RIGHT}",
            score=0.55,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="PHONE_NUMBER",
            name="TaiwanPhoneRecognizer",
            supported_language="zh",
            patterns=self.PATTERNS,
            context=["電話", "手機", "聯絡", "撥打", "分機"],
        )


class TaiwanNationalIDRecognizer(PatternRecognizer):
    """National ID `[A-Z][1289]\\d{8}` with official alphabet-weight checksum."""

    PATTERNS: ClassVar[list[Pattern]] = [
        Pattern(
            name="tw_national_id",
            regex=rf"{_ASCII_BOUND_LEFT}[A-Z][1289]\d{{8}}{_ASCII_BOUND_RIGHT}",
            score=0.4,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="TW_ID",
            name="TaiwanNationalIDRecognizer",
            supported_language="zh",
            patterns=self.PATTERNS,
            context=["身分證", "身份證", "統號", "身分證字號"],
        )

    def validate_result(self, pattern_text: str) -> bool:
        return is_valid_tw_national_id(pattern_text)


class TaiwanSchoolRecognizer(EntityRecognizer):
    """K-12 school names: suffix-anchored so verbs like 去/在 are not swallowed."""

    SUFFIXES: ClassVar[tuple[str, ...]] = (
        "國民小學",
        "國民中學",
        "高級中學",
        "幼兒園",
        "國小",
        "國中",
        "高中",
        "高職",
        "附幼",
    )
    _STOP = set("的在去到從與和是及於讀念上來把被讓給跟向往就")
    _PREFIX_MIN = 2
    _PREFIX_MAX = 6

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["SCHOOL"],
            name="TaiwanSchoolRecognizer",
            supported_language="zh",
        )
        self._suffix_re = re.compile("|".join(re.escape(item) for item in self.SUFFIXES))

    def load(self) -> None:
        return None

    def analyze(
        self,
        text: str,
        entities: list[str],
        nlp_artifacts: NlpArtifacts | None = None,
    ) -> list[RecognizerResult]:
        if entities and "SCHOOL" not in entities:
            return []
        results: list[RecognizerResult] = []
        seen: set[tuple[int, int]] = set()
        for match in self._suffix_re.finditer(text):
            prefix_start = match.start()
            taken = 0
            cursor = match.start()
            while cursor > 0 and taken < self._PREFIX_MAX:
                previous = text[cursor - 1]
                if previous in self._STOP or not re.match(rf"[{_CJK}]", previous):
                    break
                cursor -= 1
                taken += 1
                prefix_start = cursor
            if taken < self._PREFIX_MIN:
                continue
            span = (prefix_start, match.end())
            if span in seen:
                continue
            seen.add(span)
            results.append(
                RecognizerResult(
                    entity_type="SCHOOL",
                    start=prefix_start,
                    end=match.end(),
                    score=0.85,
                )
            )
        return results


class TaiwanLocationRecognizer(PatternRecognizer):
    """Taiwan street addressing: city/county, district, road, section, lane, number, floor."""

    _CITY = (
        r"(?:台|臺)北市|(?:新北|桃園|(?:台|臺)中|(?:台|臺)南|高雄|基隆|新竹|嘉義)市|"
        r"(?:新竹|苗栗|彰化|南投|雲林|嘉義|屏東|宜蘭|花蓮|(?:台|臺)東|澎湖|金門|連江)縣"
    )
    _DISTRICT = rf"[{_CJK}]{{1,4}}(?:區|鄉|鎮|市)"
    _ROAD = rf"[{_CJK}0-9]{{1,10}}(?:路|街|大道)"
    _SECTION = r"[一二三四五六七八九十0-9]+段"
    _LANE = r"[0-9]+巷(?:[0-9]+弄)?"
    _NUMBER = r"[0-9]+號(?:之[0-9]+)?"
    _FLOOR = r"(?:[0-9]+樓(?:之[0-9]+)?|[0-9]+[Ff])"

    PATTERNS: ClassVar[list[Pattern]] = [
        Pattern(
            name="tw_full_address",
            regex=(
                rf"(?:{_CITY})(?:{_DISTRICT})?(?:{_ROAD})?(?:{_SECTION})?"
                rf"(?:{_LANE})?(?:{_NUMBER})?(?:{_FLOOR})?"
            ),
            score=0.7,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="LOCATION",
            name="TaiwanLocationRecognizer",
            supported_language="zh",
            patterns=self.PATTERNS,
            context=["住在", "地址", "家裡", "家裡在", "家住"],
        )

    def invalidate_result(self, pattern_text: str) -> bool:
        """Drop city-only hits; require district or a street-level component."""
        has_district = bool(re.search(r"(?:區|鄉|鎮)", pattern_text))
        has_street = bool(re.search(r"(?:路|街|大道|段|巷|弄|號|樓)", pattern_text))
        return not (has_district or has_street)


class ChinesePersonRecognizer(EntityRecognizer):
    """Chinese names with common surnames and child-context cues (我叫/我是/同學/小朋友)."""

    COMPOUND_SURNAMES: ClassVar[tuple[str, ...]] = (
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
    SINGLE_SURNAMES: ClassVar[str] = (
        "陳林黃張李王吳劉蔡楊許鄭謝郭洪邱曾廖賴徐周葉蘇莊呂江何蕭羅高潘簡朱鍾游"
        "彭詹胡施沈余盧梁趙顏柯翁魏孫戴范鄧曹傅薛丁卓馬蔣藍宋杜姚石龔馮于韓唐阮"
        "童白溫方連田董鄒巫尤錢尹黎易湯陶康姜武賀嚴顧孟龍萬段雷鮑史崔孔白方"
    )

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["PERSON"],
            name="ChinesePersonRecognizer",
            supported_language="zh",
        )
        surname = rf"(?:{'|'.join(self.COMPOUND_SURNAMES)}|[{self.SINGLE_SURNAMES}])"
        given = rf"[{_CJK}]{{1,2}}"
        name = rf"(?P<name>{surname}{given})"
        self._patterns = (
            re.compile(rf"(?:我叫|我是|名叫|名字是|名字叫|我的名字是)\s*{name}"),
            re.compile(rf"{name}(?=同學|小朋友|老師)"),
            re.compile(rf"(?:同學|小朋友)\s*{name}"),
        )

    def load(self) -> None:
        return None

    def analyze(
        self,
        text: str,
        entities: list[str],
        nlp_artifacts: NlpArtifacts | None = None,
    ) -> list[RecognizerResult]:
        if entities and "PERSON" not in entities:
            return []
        results: list[RecognizerResult] = []
        seen: set[tuple[int, int]] = set()
        for pattern in self._patterns:
            for match in pattern.finditer(text):
                start, end = match.span("name")
                span = (start, end)
                if span in seen or start == end:
                    continue
                seen.add(span)
                results.append(
                    RecognizerResult(
                        entity_type="PERSON",
                        start=start,
                        end=end,
                        score=0.85,
                    )
                )
        return results


def build_taiwan_recognizers() -> list[EntityRecognizer]:
    return [
        TaiwanPhoneRecognizer(),
        TaiwanNationalIDRecognizer(),
        TaiwanSchoolRecognizer(),
        TaiwanLocationRecognizer(),
        ChinesePersonRecognizer(),
    ]
