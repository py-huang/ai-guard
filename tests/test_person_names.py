from __future__ import annotations

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.analyzer import build_analyzer_engine
from safety_gateway.pii.name_eval_set import TOP_1000_FULL_NAMES
from safety_gateway.pii.taiwan_names import COMMON_FULL_NAMES, FET_PUBLIC_NAMES
from safety_gateway.vault.memory import InMemorySessionVault


def _person_spans(text: str) -> set[str]:
    engine = build_analyzer_engine()
    return {
        text[hit.start : hit.end]
        for hit in engine.analyze(text=text, language="zh")
        if hit.entity_type == "PERSON"
    }


def test_common_full_name_set_has_one_hundred() -> None:
    assert len(COMMON_FULL_NAMES) == 100
    assert len(set(COMMON_FULL_NAMES)) == 100


def test_bare_name_without_wojiao_is_person() -> None:
    assert "王小明" in _person_spans("王小明想問功課")
    assert "王小明" in _person_spans("請問，王小明明天要交作業嗎？")
    assert "張佑銓" in _person_spans("張佑銓 出軌雞雞會爛掉")


def test_top_one_thousand_moi_style_names_are_masked() -> None:
    engine = build_analyzer_engine()
    missed: list[tuple[str, list[str]]] = []
    for name in TOP_1000_FULL_NAMES:
        text = f"{name}他是同學"
        hits = [
            text[hit.start : hit.end]
            for hit in engine.analyze(text=text, language="zh")
            if hit.entity_type == "PERSON"
        ]
        if name not in hits:
            missed.append((name, hits))
    assert not missed, missed[:20]


def test_top_one_hundred_common_names_are_masked() -> None:
    engine = build_analyzer_engine()
    for name in COMMON_FULL_NAMES:
        text = f"{name}想問功課"
        hits = [
            text[hit.start : hit.end]
            for hit in engine.analyze(text=text, language="zh")
            if hit.entity_type == "PERSON"
        ]
        assert name in hits, (name, hits)


def test_two_char_name_does_not_swallow_shuo() -> None:
    spans = _person_spans("黃奇說他想吃拉麵 這附近哪了有")
    assert "黃奇" in spans
    assert "黃奇說" not in spans


def test_name_inside_sentence_is_still_person() -> None:
    spans = _person_spans("幫忙黃奇買拉麵")
    assert "黃奇" in spans
    assert "黃奇買" not in spans


def test_school_word_gaozhong_is_not_a_person() -> None:
    assert "高中" not in _person_spans("我明年要升高中了")


def test_jing_qi_president_sentence_is_person() -> None:
    spans = _person_spans("井琪他是遠傳的總經理")
    assert "井琪" in spans
    assert "井琪他" not in spans


def test_fet_public_leadership_names_are_masked() -> None:
    engine = build_analyzer_engine()
    for name in FET_PUBLIC_NAMES:
        text = f"{name}他是遠傳的同事"
        hits = [
            text[hit.start : hit.end]
            for hit in engine.analyze(text=text, language="zh")
            if hit.entity_type == "PERSON"
        ]
        assert name in hits, (name, hits)


def test_chen_family_place_is_not_a_person() -> None:
    assert "陳家" not in _person_spans("新竹陳家附近有圖書館嗎？")


def test_how_to_speed_up_reaction_is_not_a_person() -> None:
    text = "如何讓反應變得更快？"
    assert _person_spans(text) == set()
    assert "何讓反" not in _person_spans(text)


def test_where_is_this_place_is_not_a_person() -> None:
    text = "這個地方在哪裡 好漂亮"
    assert _person_spans(text) == set()
    assert "方在哪" not in _person_spans(text)


def test_tomorrow_temperature_is_not_a_person() -> None:
    text = "我想知道明天的氣溫幾度"
    assert _person_spans(text) == set()
    assert "溫幾度" not in _person_spans(text)


_MATH_WORD_PROBLEMS = (
    "小宇有 15 顆草莓，吃了 7 顆，媽媽又買給他 8 顆，現在小宇一共有幾顆草莓？",
    "體育課排隊時，小明排在第 14 個，小華排在小明前面 5 個位置，小華排在第幾個？",
    "桌上有 4 個盤子，每個盤子裡都放 3 顆蘋果，桌上一共有幾顆蘋果？",
    "一枝鉛筆 8 元，小美買了 2 枝，付了一張 50 元鈔票，應該找回多少元？",
    "時針指在 4 和 5 之間，分針指在 6，請問現在是幾點幾分？",
    "文具店一盒彩色筆 120 元，今天買 3 盒特價現折 50 元，買 3 盒一共要付多少元？",
    "老師有 85 顆糖果，平均分給 9 位小朋友，每人可以分到幾顆？還剩下幾顆？",
    "一盒披薩平分成 8 片，弟弟吃了 2/8 盒，哥哥吃了 3/8 盒，兩人一共吃了幾分之幾盒？還剩下幾片？",
    "一條緞帶長 3.6 公尺，包裝禮物用去 1.8 公尺，綁花束用去 0.9 公尺，還剩下幾公尺？",
    "一個長方形花圃的長是 12 公尺、寬是 8 公尺，這個花圃的周長是多少公尺？面積是多少平方公尺？",
    "一包米重 2 公斤 350 公克，吃掉 800 公克後，還剩下幾公斤幾公克？",
    "小玲有一些貼紙，每 6 張裝一袋剛好分完，每 8 張裝一袋也剛好分完，小玲最少有幾張貼紙？",
    "一瓶果汁有 3/4 公升，小明喝了其中的 2/5，小明喝了多少公升的果汁？",
    "小華騎腳踏車的分速是 200 公尺，他從學校騎到圖書館花了 15 分鐘，這段路程是多少公里？",
    "調配一杯奶茶，紅茶和牛奶的容量比是 5 : 2。如果用了 350 毫升的紅茶，需要加入多少毫升的牛奶？",
    "一件外套定價 1500 元，週年慶打八五折出售，這件外套特價是多少元？",
    "一個長 20 公分、寬 15 公分、高 10 公分的長方體容器，裝滿水是多少毫升？也就是幾公升？",
    "農場裡有雞和兔子共 20 隻，數一數牠們的腳一共有 56 隻，農場裡有幾隻雞？幾隻兔子？",
)


def test_grade_math_word_problems_are_not_person() -> None:
    leaked = []
    for text in _MATH_WORD_PROBLEMS:
        spans = _person_spans(text)
        if spans:
            leaked.append((text, sorted(spans)))
    assert not leaked, leaked


def test_homework_prompt_still_has_no_person() -> None:
    engine = build_analyzer_engine()
    types = {hit.entity_type for hit in engine.analyze(text="今天作業寫在黑板上，我們可以一起想", language="zh")}
    assert "PERSON" not in types


def test_session_reuses_given_name_and_surname_classmate() -> None:
    vault = InMemorySessionVault()
    gateway = AISafetyGateway(vault=vault)
    first = gateway.process_inbound("alias-1", "陳小明想問數學")
    assert "<PERSON_1>" in first.processed_text
    assert "陳小明" not in first.processed_text

    given = gateway.process_inbound("alias-1", "那小明這題怎麼寫")
    assert "<PERSON_1>" in given.processed_text
    assert "小明" not in given.processed_text

    classmate = gateway.process_inbound("alias-1", "陳同學明天請假")
    assert "<PERSON_1>" in classmate.processed_text
    assert "陳同學" not in classmate.processed_text
    assert vault.list_mappings("alias-1")["<PERSON_1>"] == "陳小明"
