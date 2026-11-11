"""Name detection precision/recall regressions (see scripts/eval_pii_names.py for the corpus numbers)."""

from __future__ import annotations

import pytest

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.name_stoplist import GLUED_SURNAMES, STOP_WORDS
from safety_gateway.pii.taiwan_names import is_everyday_word


@pytest.fixture(scope="module")
def gateway() -> AISafetyGateway:
    return AISafetyGateway()


def _out(gateway: AISafetyGateway, text: str) -> str:
    return gateway.sanitize_text("precision", text).processed_text


@pytest.mark.parametrize(
    ("text", "name"),
    [
        ("昨天王小明來學校了", "王小明"),
        ("今天林淑芬沒有交作業", "林淑芬"),
        ("我同學小李沒來", "小李"),
        ("請問張雅婷在嗎", "張雅婷"),
        ("老師說黃建宏很認真", "黃建宏"),
        ("他的名字是李和音", "李和音"),
        ("我認識一個人叫歐陽志遠", "歐陽志遠"),
        ("我叫約翰，今年十歲", "約翰"),
        ("我的名字是安娜，我在讀三年級", "安娜"),
        ("我叫Amy，今年十歲", "Amy"),
        ("My name is Tom Lee", "Tom Lee"),
        ("Hi, I'm Jessica", "Jessica"),
        ("call me Tom", "Tom"),
    ],
)
def test_real_names_are_still_masked(gateway: AISafetyGateway, text: str, name: str) -> None:
    assert name not in _out(gateway, text)


@pytest.mark.parametrize(
    "text",
    [
        "他是中國人，她是芬蘭人",
        "我們一個人去公園",
        "請把這句話翻譯成德文",
        "西方國家的文化跟我們不一樣",
        "請幫我把句子改得更簡潔",
        "黃瓜和李子都是蔬果",
        "我想寫一首史詩",
        "這個 Java程式 有 bug",
        "I'm tired and this is great",
        "我叫媽媽來吃飯",
        "我叫你來幫忙",
        "我叫了一份早餐",
    ],
)
def test_ordinary_text_is_left_alone(gateway: AISafetyGateway, text: str) -> None:
    assert _out(gateway, text) == text


def test_a_url_is_masked_as_a_url_not_as_a_person(gateway: AISafetyGateway) -> None:
    result = gateway.sanitize_text("precision", "請看 https://news.example.com/a/b 這篇")
    assert [e.entity_type for e in result.entities] == ["URL"]


def test_this_is_does_not_introduce_a_name(gateway: AISafetyGateway) -> None:
    assert _out(gateway, "This is Taiwan") == "This is Taiwan"


def test_the_derived_lexicon_is_words_only_and_keeps_nickname_forms() -> None:
    assert STOP_WORDS and GLUED_SURNAMES
    assert all(2 <= len(word) <= 4 for word in STOP_WORDS)
    assert "小李" not in GLUED_SURNAMES  # 小李 / 老王 / 阿明 are how people address each other
    assert is_everyday_word("生成美國", 1, 3)  # 成美 glued to the 生 in front of it
    assert not is_everyday_word("請問王小明在嗎", 2, 5)
