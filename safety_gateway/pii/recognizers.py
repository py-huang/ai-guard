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
_CLASS_UNIT = r"[一二三四五六七八九十兩0-9]{1,2}年[一二三四五六七八九十甲乙丙丁0-9]{1,2}班"


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
    _NUMBER = r"[0-9]+(?:號|号)(?:之[0-9]+)?"
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
        has_street = bool(re.search(r"(?:路|街|大道|段|巷|弄|號|号|樓)", pattern_text))
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
            re.compile(
                rf"(?:我叫|我是|名叫|名字是|名字叫|我的名字是)\s*{_CLASS_UNIT}的?\s*{name}"
            ),
            re.compile(rf"{_CLASS_UNIT}的?\s*{name}"),
            re.compile(rf"(?:姓名|學生姓名|名牌|名札)[:：]?\s*{name}"),
            re.compile(rf"(?:這是|他是|她是|他叫|她叫|班上的|班上)\s*{name}"),
            re.compile(rf"(?:班導師|級任老師|導師|老師)\s*叫\s*{name}"),
            re.compile(rf"(?:把|拿)\s*{name}(?=的照片|的相片|來搞怪|的臉)"),
            re.compile(rf"{name}(?=同學|小朋友|老師|的照片|的相片)"),
            re.compile(rf"(?:同學|小朋友)\s*{name}"),
            re.compile(rf"{name}\s*(?=同學|小朋友|老師)"),
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


class EnglishPersonRecognizer(EntityRecognizer):
    """Latin-script names in a 繁中句子 — counterpart of Presidio's spaCy PERSON."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["PERSON"],
            name="EnglishPersonRecognizer",
            supported_language="zh",
        )
        given = r"[A-Za-z][a-z]{1,20}"
        full = rf"(?P<name>{given}(?:\s+{given}){{0,2}})"
        self._patterns = (
            re.compile(
                rf"(?:我叫|名叫|名字是|名字叫|我的名字是|My name is)\s*{full}",
                re.IGNORECASE,
            ),
            re.compile(rf"(?:同學|小朋友)\s*{full}"),
            re.compile(rf"{full}\s*(?=同學|小朋友)"),
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
                        score=0.8,
                    )
                )
        return results


class TaiwanDateRecognizer(PatternRecognizer):
    """民國 / 西元年月日 — counterpart of Presidio DATE_TIME. Bare「3月」不算。"""

    PATTERNS: ClassVar[list[Pattern]] = [
        Pattern(
            name="roc_date",
            regex=r"民國\s*\d{2,3}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日",
            score=0.75,
        ),
        Pattern(
            name="cjk_gregorian_date",
            regex=r"(?:19|20)\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日",
            score=0.7,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="DATE_TIME",
            name="TaiwanDateRecognizer",
            supported_language="zh",
            patterns=self.PATTERNS,
            context=["生日", "日期", "民國"],
        )


class _LabeledValueRecognizer(EntityRecognizer):
    """Cue words in the regex; only the identifier span is emitted."""

    def __init__(
        self,
        *,
        entity_type: str,
        name: str,
        patterns: tuple[re.Pattern[str], ...],
        score: float,
    ) -> None:
        super().__init__(
            supported_entities=[entity_type],
            name=name,
            supported_language="zh",
        )
        self._entity_type = entity_type
        self._patterns = patterns
        self._score = score

    def load(self) -> None:
        return None

    def analyze(
        self,
        text: str,
        entities: list[str],
        nlp_artifacts: NlpArtifacts | None = None,
    ) -> list[RecognizerResult]:
        if entities and self._entity_type not in entities:
            return []
        results: list[RecognizerResult] = []
        seen: set[tuple[int, int]] = set()
        for pattern in self._patterns:
            for match in pattern.finditer(text):
                start, end = match.span("value")
                span = (start, end)
                if span in seen or start == end:
                    continue
                seen.add(span)
                results.append(
                    RecognizerResult(
                        entity_type=self._entity_type,
                        start=start,
                        end=end,
                        score=self._score,
                    )
                )
        return results


class TaiwanSchoolClassRecognizer(PatternRecognizer):
    """Homeroom like 三年一班 — identifying for a child even without a school name."""

    PATTERNS: ClassVar[list[Pattern]] = [
        Pattern(
            name="tw_homeroom",
            regex=_CLASS_UNIT,
            score=0.8,
        ),
    ]

    def __init__(self) -> None:
        super().__init__(
            supported_entity="SCHOOL_CLASS",
            name="TaiwanSchoolClassRecognizer",
            supported_language="zh",
            patterns=self.PATTERNS,
            context=["班", "年級", "請假", "學號", "座號"],
        )


class InstagramHandleRecognizer(_LabeledValueRecognizer):
    """Instagram / IG handle. Needs an IG cue so English words are not swallowed."""

    def __init__(self) -> None:
        ident = r"(?P<value>@?[A-Za-z][A-Za-z0-9._]{1,29})"
        cue = r"(?:IG|ig|I\.G\.|Instagram|instagram|insta)"
        super().__init__(
            entity_type="IG_HANDLE",
            name="InstagramHandleRecognizer",
            score=0.92,
            patterns=(
                re.compile(rf"(?<![A-Za-z]){cue}\s*(?:帳號)?[:：是為]?\s*{ident}"),
            ),
        )


class TaiwanStudentIdRecognizer(_LabeledValueRecognizer):
    """學號／座號. Label required so homework numbers are not swallowed."""

    def __init__(self) -> None:
        super().__init__(
            entity_type="STUDENT_ID",
            name="TaiwanStudentIdRecognizer",
            score=0.9,
            patterns=(
                re.compile(rf"(?:學號)[:：是為]?\s*(?P<value>\d{{3,10}})"),
            ),
        )


class TaiwanPassportRecognizer(_LabeledValueRecognizer):
    """護照號碼 — counterpart of US_PASSPORT. 9 chars, not the 10-char national ID."""

    def __init__(self) -> None:
        ident = r"(?P<value>[A-Z]{1,2}\d{7,8})"
        super().__init__(
            entity_type="TW_PASSPORT",
            name="TaiwanPassportRecognizer",
            score=0.9,
            patterns=(
                re.compile(rf"(?:護照號碼|護照號|護照)[:：是為]?\s*{ident}"),
            ),
        )


class TaiwanDriverLicenseRecognizer(_LabeledValueRecognizer):
    """駕照字號 — counterpart of US_DRIVER_LICENSE."""

    def __init__(self) -> None:
        ident = r"(?P<value>[A-Z0-9]{8,12})"
        super().__init__(
            entity_type="TW_DRIVER_LICENSE",
            name="TaiwanDriverLicenseRecognizer",
            score=0.88,
            patterns=(
                re.compile(rf"(?:駕照號碼|駕照字號|駕駛執照|駕照)[:：是為]?\s*{ident}"),
            ),
        )


class TaiwanBankAccountRecognizer(_LabeledValueRecognizer):
    """郵局/銀行帳號 — counterpart of US_BANK_NUMBER. Needs a label so raw digits pass."""

    def __init__(self) -> None:
        ident = r"(?P<value>\d{8,16})"
        super().__init__(
            entity_type="TW_BANK_ACCOUNT",
            name="TaiwanBankAccountRecognizer",
            score=0.9,
            patterns=(
                re.compile(rf"(?:郵局帳號|銀行帳號|匯款帳號|帳號)[:：是為]?\s*{ident}"),
            ),
        )


class TaiwanOrganizationRecognizer(EntityRecognizer):
    """公司／醫院／基金會 — counterpart of spaCy ORGANIZATION. Suffix-anchored like schools."""

    SUFFIXES: ClassVar[tuple[str, ...]] = (
        "股份有限公司",
        "有限公司",
        "醫院",
        "基金會",
        "協會",
        "公司",
    )
    _STOP = set("的是在去到從與和及於讀念上來把被讓給跟向往就他她我你")
    _GENERIC_PREFIXES: ClassVar[set[str]] = {
        "我們",
        "你們",
        "他們",
        "這間",
        "那間",
        "一間",
        "某間",
        "自己",
        "其他",
        "相關",
        "什麼",
    }

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["ORGANIZATION"],
            name="TaiwanOrganizationRecognizer",
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
        if entities and "ORGANIZATION" not in entities:
            return []
        results: list[RecognizerResult] = []
        seen: set[tuple[int, int]] = set()
        for match in self._suffix_re.finditer(text):
            suffix = match.group(0)
            min_prefix = 3 if suffix == "公司" else 2
            taken = 0
            cursor = match.start()
            prefix_start = match.start()
            while cursor > 0 and taken < 12:
                previous = text[cursor - 1]
                if previous in self._STOP or not re.match(rf"[{_CJK}]", previous):
                    break
                cursor -= 1
                taken += 1
                prefix_start = cursor
            prefix = text[prefix_start : match.start()]
            if taken < min_prefix or prefix in self._GENERIC_PREFIXES:
                continue
            span = (prefix_start, match.end())
            if span in seen:
                continue
            seen.add(span)
            results.append(
                RecognizerResult(
                    entity_type="ORGANIZATION",
                    start=prefix_start,
                    end=match.end(),
                    score=0.7,
                )
            )
        return results


def build_taiwan_recognizers() -> list[EntityRecognizer]:
    return [
        TaiwanPhoneRecognizer(),
        TaiwanNationalIDRecognizer(),
        TaiwanSchoolRecognizer(),
        TaiwanSchoolClassRecognizer(),
        TaiwanStudentIdRecognizer(),
        InstagramHandleRecognizer(),
        TaiwanLocationRecognizer(),
        ChinesePersonRecognizer(),
        EnglishPersonRecognizer(),
        TaiwanDateRecognizer(),
        TaiwanPassportRecognizer(),
        TaiwanDriverLicenseRecognizer(),
        TaiwanBankAccountRecognizer(),
        TaiwanOrganizationRecognizer(),
    ]
