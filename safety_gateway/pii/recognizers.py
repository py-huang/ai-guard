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
from safety_gateway.pii.taiwan_names import (
    COMPOUND_SURNAMES,
    SINGLE_SURNAMES,
    is_everyday_word,
    resolved_person_span,
    surname_prefix,
    vet_uncued_given,
)

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


class TaiwanNationalIDRecognizer(EntityRecognizer):
    """National ID: checksum-valid always; format-only when 身分證 cue is nearby."""

    _ID = re.compile(rf"{_ASCII_BOUND_LEFT}([A-Z][1289]\d{{8}}){_ASCII_BOUND_RIGHT}")
    _CUE = re.compile(r"身分證|身份證|統號|身分證字號")
    # "A 123 456 789", "a-123456789", lowercase: kids and speech-to-text do not type it cleanly.
    _LOOSE_ID = re.compile(
        rf"{_ASCII_BOUND_LEFT}([A-Za-z])[ \-]?([1289])(?:[ \-]?\d){{8}}{_ASCII_BOUND_RIGHT}"
    )

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["TW_ID"],
            name="TaiwanNationalIDRecognizer",
            supported_language="zh",
        )

    def load(self) -> None:
        return None

    def analyze(
        self,
        text: str,
        entities: list[str],
        nlp_artifacts: NlpArtifacts | None = None,
    ) -> list[RecognizerResult]:
        if entities and "TW_ID" not in entities:
            return []
        results: list[RecognizerResult] = []
        for match in self._ID.finditer(text):
            value = match.group(1)
            window = text[max(0, match.start() - 12) : match.end() + 4]
            cued = bool(self._CUE.search(window))
            if is_valid_tw_national_id(value):
                score = 0.85
            elif cued:
                score = 0.55
            else:
                continue
            results.append(
                RecognizerResult(
                    entity_type="TW_ID",
                    start=match.start(1),
                    end=match.end(1),
                    score=score,
                )
            )
        seen = {(hit.start, hit.end) for hit in results}
        for match in self._LOOSE_ID.finditer(text):
            span = (match.start(), match.end())
            if span in seen:
                continue
            compact = re.sub(r"[ \-]", "", match.group(0)).upper()
            window = text[max(0, match.start() - 12) : match.end() + 4]
            if is_valid_tw_national_id(compact):
                score = 0.85
            elif self._CUE.search(window):
                score = 0.55
            else:
                continue
            results.append(
                RecognizerResult(entity_type="TW_ID", start=span[0], end=span[1], score=score)
            )
        return results


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

    _PLACE_CONNECTIVES = frozenset("和上來到及")
    _PRONOUNS = frozenset("我你他她它們咱您")

    def _scan_prefix(self, text: str, end: int, *, lenient: bool) -> tuple[int, int]:
        start, taken, cursor = end, 0, end
        while cursor > 0 and taken < self._PREFIX_MAX:
            previous = text[cursor - 1]
            if not re.match(rf"[{_CJK}]", previous):
                break
            if previous in self._STOP and not (lenient and previous in self._PLACE_CONNECTIVES):
                break
            if lenient and previous in self._PRONOUNS:
                break
            cursor -= 1
            taken += 1
            start = cursor
        return start, taken

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
            prefix_start, taken = self._scan_prefix(text, match.start(), lenient=False)
            if taken < self._PREFIX_MIN:
                # 和平國小, 上林國小: the place name itself starts with a connective. Retry once,
                # still refusing pronouns so "我和國小的同學" is not read as a school.
                prefix_start, taken = self._scan_prefix(text, match.start(), lenient=True)
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
    # Without a city or district to anchor it, a road name is short ("復興路", "中山北路"); the
    # long form would swallow the carrier sentence ("聯絡我的方式是中華路376號").
    _ROAD_SHORT = rf"[{_CJK}0-9]{{1,4}}(?:路|街|大道)"
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
        # Children often leave the city out: "中正區復興路371號", "光復路245號".
        Pattern(
            name="tw_address_no_city",
            regex=(
                rf"(?![在是住家的我你他她有到寄去來])(?:[{_CJK}]{{2,3}}(?:區|鄉|鎮))?{_ROAD_SHORT}(?:{_SECTION})?(?:{_LANE})?"
                rf"{_NUMBER}(?:{_FLOOR})?"
            ),
            score=0.65,
        ),
        Pattern(
            name="tw_english_address",
            regex=(
                r"(?:(?:\d+F\.,\s*)?No\.\s*\d+,\s*(?:Ln\.\s*\d+,\s*)?(?:Sec\.\s*\d+,\s*)?"
                r"[A-Za-z .]{4,40}(?:Rd|St|Blvd)\.,?\s*[A-Za-z .]{3,40}"
                r"(?:Dist\.)?,?\s*(?:New\s+)?[A-Za-z ]{3,20}City[^,]{0,20})"
            ),
            score=0.65,
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
        has_street = bool(re.search(r"(?:路|街|大道|段|巷|弄|號|号|樓|Rd|St|Blvd|No\.)", pattern_text))
        return not (has_district or has_street)


class ChinesePersonRecognizer(EntityRecognizer):
    """Chinese names with common surnames and child-context cues (我叫/我是/同學/小朋友)."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["PERSON"],
            name="ChinesePersonRecognizer",
            supported_language="zh",
        )
        surname = rf"(?:{'|'.join(COMPOUND_SURNAMES)}|[{SINGLE_SURNAMES}])"
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
            re.compile(rf"{name}(?=同學|小朋友|老師|先生|小姐|女士|的照片|的相片)"),
            re.compile(rf"(?:同學|小朋友)\s*{name}"),
            re.compile(rf"{name}\s*(?=同學|小朋友|老師|先生|小姐|女士)"),
            re.compile(rf"(?:我跟|我和|我與|跟|和|與)\s*{name}(?=先生|小姐|女士|老師|同學)"),
        )
        # "我叫約翰，今年十歲": announced as a name but with no Taiwan surname (foreign or given-only).
        # Ends at punctuation or a following clause so "我叫媽媽來" is not read as a name.
        self._announced = re.compile(
            rf"(?:我叫|我的名字是|我的名字叫|名字叫|我的英文名字是)\s*(?P<name>[{_CJK}]{{2,3}})"
            rf"(?=$|[，,。！？!?\s、；;]|今年|我是|我在|我住|我喜歡|我有|我讀|我念)"
        )
        # A surname with a title, or announced as one's surname, is a naming cue in itself.
        self._surname_cues = (
            re.compile(
                rf"(?P<name>{surname}(?:先生|小姐|女士|經理|副理|主任|老闆娘|老闆|醫師|律師|教授|校長|董事長|總經理|老師|同學|爸爸|媽媽|阿姨|叔叔|伯伯|伯母|舅舅|阿嬤|奶奶|爺爺))"
            ),
            re.compile(rf"(?:我姓|敝姓|免貴姓|本姓)(?P<name>{surname})"),
        )
        # 姓＋名 after a start, comma, space, or 請問／是: no naming cue, so it is vetted like the sweep.
        self._loose = re.compile(
            rf"(?:^|(?<=[\s，,。！？；;：:\n、問請是有跟和與給把被對向找幫讓叫在到從用看聽說的])){name}"
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
                raw = match.span("name")
                span = resolved_person_span(text, raw[0], raw[1])
                if span is None or span in seen or span[0] == span[1]:
                    continue
                start, end = span
                seen.add(span)
                results.append(
                    RecognizerResult(
                        entity_type="PERSON",
                        start=start,
                        end=end,
                        score=0.85,
                    )
                )
        for match in self._announced.finditer(text):
            span = match.span("name")
            if span in seen or not _is_announceable_name(match.group("name")):
                continue
            seen.add(span)
            results.append(RecognizerResult(entity_type="PERSON", start=span[0], end=span[1], score=0.8))
        for pattern in self._surname_cues:
            for match in pattern.finditer(text):
                span = match.span("name")
                if span in seen:
                    continue
                seen.add(span)
                results.append(
                    RecognizerResult(entity_type="PERSON", start=span[0], end=span[1], score=0.85)
                )
        for match in self._loose.finditer(text):
            raw = match.span("name")
            span = resolved_person_span(text, raw[0], raw[1])
            if span is None or span[0] == span[1]:
                continue
            span = _vet_uncued(text, span)
            if span is None or span in seen:
                continue
            seen.add(span)
            results.append(
                RecognizerResult(entity_type="PERSON", start=span[0], end=span[1], score=0.85)
            )
        for start, end in _scan_plausible_names(text):
            span = (start, end)
            if span in seen:
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


# Words that can follow 我叫 without being anyone's name: people to address, pronouns, roles.
_NOT_ANNOUNCED = frozenset(
    {
        "爸爸", "媽媽", "爸媽", "哥哥", "姊姊", "姐姐", "弟弟", "妹妹", "爺爺", "奶奶", "阿嬤", "阿公", "阿姨",
        "叔叔", "伯伯", "舅舅", "老師", "同學", "大家", "你們", "我們", "他們", "她們", "小狗", "小貓", "機器人",
        "警察", "醫生", "助理", "老闆", "朋友", "小朋友", "外送", "計程車",
    }
)


def _is_announceable_name(word: str) -> bool:
    return (
        word not in _NOT_ANNOUNCED
        and word[0] not in "你我他她它這那"
        and not any(char in "的了是在不有和與為嗎呢吧來去幫給請" for char in word)
    )


def _vet_uncued(text: str, span: tuple[int, int]) -> tuple[int, int] | None:
    """Vet a candidate that had no naming cue around it (the sweep and the loose pattern).

    Returns the (possibly trimmed) span, or ``None`` when the given-name part is not name-like.
    """
    if is_everyday_word(text, span[0], span[1]):
        return None
    segment = text[span[0] : span[1]]
    chars = "".join(ch for ch in segment if "\u4e00" <= ch <= "\u9fa5")
    surname = surname_prefix(chars)
    if not surname or len(chars) != len(segment):
        return None
    kept = vet_uncued_given(surname, chars[len(surname) :])
    if kept is None:
        return None
    return span[0], span[0] + len(surname) + len(kept)


def _scan_plausible_names(text: str) -> list[tuple[int, int]]:
    """High-recall sweep: any 姓＋1–2 名 window, prefer the longer span."""
    found: list[tuple[int, int]] = []
    index = 0
    length = len(text)
    while index < length:
        prefix = surname_prefix(text[index : index + 2])
        if not prefix:
            index += 1
            continue
        max_end = min(index + len(prefix) + 2, length)
        span = resolved_person_span(text, index, max_end)
        span = _vet_uncued(text, span) if span is not None else None
        if span is not None:
            found.append(span)
        index += 1
    return found


class EnglishPersonRecognizer(EntityRecognizer):
    """Latin-script names in a 繁中句子 — counterpart of Presidio's spaCy PERSON."""

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["PERSON"],
            name="EnglishPersonRecognizer",
            supported_language="zh",
        )
        given = r"[A-Z][a-z]{1,20}(?:-[A-Z][a-z]{1,20})?"
        full = rf"(?P<name>{given}(?:\s+{given}){{0,2}})"
        self._patterns = (
            re.compile(
                rf"(?:我叫|名叫|名字是|名字叫|我的名字是|My name is|我是|填寫的是|申請人)\s*{full}",
            ),
            re.compile(rf"(?:同學|小朋友|乘客名單有)\s*{full}"),
            re.compile(rf"{full}\s*(?=同學|小朋友|的健保卡)"),
            re.compile(rf"(?:我是)(?P<name>小[{_CJK}])(?=的媽媽|的爸爸|的家長)"),
            re.compile(rf"(?:傳統姓名|英文姓名)[，,是為]*\s*{full}"),
            re.compile(rf"(?P<name>{given}\s+{given})(?=，|。|和Lee|和)"),
            # "Hi, I'm Jessica" / "call me Tom": an introduction, whatever the surrounding script.
            re.compile(rf"(?i:\bI['’]m|\bI am|\bIm|\bcall me|\bmy name['’]s)\s+{full}\b"),
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


class TaiwanDateRecognizer(EntityRecognizer):
    """Only personal birthdays — not 預約／作業／起租日."""

    _DATES = (
        re.compile(r"民國\s*\d{2,3}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"),
        re.compile(r"(?:19|20)\d{2}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"),
        re.compile(r"(?<![0-9])1[0-2]\d\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日"),
        re.compile(r"(?<![0-9])1[0-2]\d[./]\d{1,2}[./]\d{1,2}(?![0-9])"),
        re.compile(r"(?:19|20)\d{2}[-/]\d{1,2}[-/]\d{1,2}"),
        re.compile(r"[甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥]年[^，。]{0,8}(?:初[一二三四五六七八九十]|[一二三四五六七八九十]+日)"),
        re.compile(r"(?<![0-9])\d{2}年次"),
        re.compile(r"(?<![0-9])\d{2}/\d{1,2}/\d{1,2}(?![0-9])"),
        # 九月二十八號 / 9月28日 — year omitted, only with 生日 cue
        re.compile(
            r"(?:1[0-2]|[1-9]|十[一二]|[正一二三四五六七八九十])\s*月\s*"
            r"(?:3[01]|[12]\d|[1-9]|三十[一]?|二十[一二三四五六七八九]?|"
            r"[一二]?十[一二三四五六七八九]?|[一二三四五六七八九]|廿[一二三四五六七八九]?)"
            r"\s*(?:號|日)"
        ),
    )
    # (?<!發)生日：不要把「事故發生日期」裡的「生日」當線索
    _CUE = re.compile(r"(?<!發)生日|出生年月日|出生日期|農曆生日|出生|birthday|(?<![0-9])\d{2}年次", re.IGNORECASE)

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["DATE_TIME"],
            name="TaiwanDateRecognizer",
            supported_language="zh",
        )

    def load(self) -> None:
        return None

    def analyze(
        self,
        text: str,
        entities: list[str],
        nlp_artifacts: NlpArtifacts | None = None,
    ) -> list[RecognizerResult]:
        if entities and "DATE_TIME" not in entities:
            return []
        results: list[RecognizerResult] = []
        seen: set[tuple[int, int]] = set()
        for pattern in self._DATES:
            for match in pattern.finditer(text):
                window = text[max(0, match.start() - 20) : match.end() + 6]
                if not self._CUE.search(window):
                    continue
                span = (match.start(), match.end())
                if span in seen:
                    continue
                seen.add(span)
                results.append(
                    RecognizerResult(
                        entity_type="DATE_TIME",
                        start=match.start(),
                        end=match.end(),
                        score=0.8,
                    )
                )
        return results


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


class CuedEmailRecognizer(_LabeledValueRecognizer):
    """Catch 信箱 addresses Presidio TLD checks sometimes drop."""

    def __init__(self) -> None:
        ident = r"(?P<value>[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})"
        super().__init__(
            entity_type="EMAIL_ADDRESS",
            name="CuedEmailRecognizer",
            score=0.9,
            patterns=(
                re.compile(rf"(?:信箱|寄到)[:：]?\s*{ident}"),
            ),
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


class LineIdRecognizer(_LabeledValueRecognizer):
    """LINE ID. Needs an explicit ``ID``/``帳號``/colon so "line up" or "Line is" is left alone."""

    def __init__(self) -> None:
        ident = r"(?P<value>[A-Za-z0-9][A-Za-z0-9._-]{3,19})"
        marker = r"(?:\s*(?:ID|id|Id|帳號)\s*[:：是為]?|\s*[:：是為])"
        super().__init__(
            entity_type="LINE_ID",
            name="LineIdRecognizer",
            score=0.92,
            patterns=(re.compile(rf"(?<![A-Za-z])(?:LINE|Line|line){marker}\s*{ident}"),),
        )


class ObfuscatedEmailRecognizer(_LabeledValueRecognizer):
    """``name at gmail dot com`` / ``name＠gmail.com`` / ``name小老鼠gmail點com``."""

    def __init__(self) -> None:
        local = r"[A-Za-z0-9][A-Za-z0-9._%+-]{1,40}"
        at = r"\s*(?:＠|\(at\)|\[at\]|小老鼠|(?<![A-Za-z])at(?![A-Za-z]))\s*"
        dot = r"\s*(?:\(dot\)|\[dot\]|點|(?<![A-Za-z])dot(?![A-Za-z])|\.)\s*"
        label = r"[A-Za-z0-9-]{1,30}"
        tld = r"(?:com|net|org|edu|gov|tw|io|co|info|me)(?![A-Za-z])"
        super().__init__(
            entity_type="EMAIL_ADDRESS",
            name="ObfuscatedEmailRecognizer",
            score=0.9,
            patterns=(
                re.compile(
                    rf"(?<![A-Za-z0-9._%+-])(?P<value>{local}{at}{label}(?:{dot}{label})*{dot}{tld})",
                    re.IGNORECASE,
                ),
            ),
        )


_CN_DIGIT = r"[零〇洞一幺二兩三四五六七八九]"


class ChineseNumeralPhoneRecognizer(_LabeledValueRecognizer):
    """Mobile numbers written or dictated as 零九一二三四五六七八 (洞=0, 幺=1 when spoken)."""

    def __init__(self) -> None:
        super().__init__(
            entity_type="PHONE_NUMBER",
            name="ChineseNumeralPhoneRecognizer",
            score=0.85,
            patterns=(
                re.compile(
                    rf"(?<!{_CN_DIGIT})(?P<value>[零〇洞]\s?九(?:\s?{_CN_DIGIT}){{8}})(?!{_CN_DIGIT})"
                ),
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
                re.compile(rf"(?:學號)[:：是為]?\s*(?P<value>[A-Z]?\d{{3,10}})"),
            ),
        )


class TaiwanPassportRecognizer(_LabeledValueRecognizer):
    """護照號碼 — counterpart of US_PASSPORT. 9 chars, not the 10-char national ID."""

    def __init__(self) -> None:
        ident = r"(?P<value>(?:[A-Z]{1,2})?\d{8,9})"
        super().__init__(
            entity_type="TW_PASSPORT",
            name="TaiwanPassportRecognizer",
            score=0.9,
            patterns=(
                re.compile(rf"(?:護照號碼|護照號|護照)(?:[，,]號碼)?[:：是為]?\s*{ident}"),
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
                re.compile(rf"(?:駕照號碼|駕照字號|駕駛執照|駕照)[^A-Z0-9]{{0,16}}{ident}"),
            ),
        )


class TaiwanBankAccountRecognizer(_LabeledValueRecognizer):
    """郵局/銀行帳號 — counterpart of US_BANK_NUMBER. Needs a label so raw digits pass."""

    def __init__(self) -> None:
        ident = r"(?P<value>\d{4,16})"
        card = r"(?P<value>(?:\d[ -]?){13,19}\d)"
        ref = r"(?P<value>[A-Z]{1,3}\d{6,12})"
        super().__init__(
            entity_type="TW_BANK_ACCOUNT",
            name="TaiwanBankAccountRecognizer",
            score=0.9,
            patterns=(
                re.compile(rf"(?:郵局帳號|銀行帳號|匯款帳號|薪轉帳戶|帳號末五碼|帳號|卡號末四碼|工號)[:：是為]?[^0-9]{{0,8}}{ident}"),
                re.compile(rf"(?:信用卡號|信用卡|卡號)[:：是為]?\s*{card}"),
                re.compile(rf"(?:保單號碼|維修單號|退貨的單號|單號|員工編號|會員)[:：是為]?\s*{ref}"),
                re.compile(
                    rf"(?:員工編號|員編|會員編號|編號|訂房代號)[:：是為]?\s*"
                    rf"(?P<value>[A-Z]{{1,3}}\d{{3,14}}|[A-Z]{{2,4}}-\d{{6,10}}|[A-Z]{{2}}\d{{4}}|\d{{6,12}})"
                ),
                re.compile(rf"(?:保單號碼)[:：是為]?\s*(?P<value>\d{{8,14}}|\d{{4}}-\d{{2}}[A-Z0-9]{{2}}\d{{6}})"),
            ),
        )


class TaiwanHouseholdNoRecognizer(_LabeledValueRecognizer):
    """戶口名簿戶號 / 稅籍編號."""

    def __init__(self) -> None:
        ident = r"(?P<value>[A-Z]?\d{7,12})"
        super().__init__(
            entity_type="TW_HOUSEHOLD_NO",
            name="TaiwanHouseholdNoRecognizer",
            score=0.88,
            patterns=(
                re.compile(rf"(?:戶口名簿)?戶號[:：是為]?\s*{ident}"),
                re.compile(rf"(?:房屋)?稅籍編號[:：是為]?[，,]?[^A-Z0-9]{{0,24}}(?P<value>[A-Z]?\d{{8,14}})"),
                re.compile(rf"戶號印著(?P<value>[A-Z]?\d{{7,12}})"),
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
        LineIdRecognizer(),
        CuedEmailRecognizer(),
        ObfuscatedEmailRecognizer(),
        ChineseNumeralPhoneRecognizer(),
        TaiwanLocationRecognizer(),
        ChinesePersonRecognizer(),
        EnglishPersonRecognizer(),
        TaiwanDateRecognizer(),
        TaiwanPassportRecognizer(),
        TaiwanDriverLicenseRecognizer(),
        TaiwanBankAccountRecognizer(),
        TaiwanHouseholdNoRecognizer(),
        TaiwanOrganizationRecognizer(),
    ]
