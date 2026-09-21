from __future__ import annotations

from safety_gateway.playground.zhuyin import to_zhuyin_parts


def test_zhuyin_annotates_hanzi_and_keeps_tokens() -> None:
    parts = to_zhuyin_parts("中心 <PERSON_1> 你好")
    hanzi = [part for part in parts if part.zhuyin]
    texts = [part.text for part in parts]
    assert "中" in texts
    assert "心" in texts
    assert any(part.text == "<PERSON_1>" and part.zhuyin is None for part in parts)
    assert all("ㄓ" in (part.zhuyin or "") or part.text != "中" for part in hanzi)
    zhong = next(part for part in parts if part.text == "中")
    xin = next(part for part in parts if part.text == "心")
    assert "ㄓ" in (zhong.zhuyin or "")
    assert "ㄒ" in (xin.zhuyin or "")


def test_zhuyin_neutral_tone_dot_goes_first() -> None:
    parts = to_zhuyin_parts("的")
    part = next(part for part in parts if part.text == "的")
    assert part.tone == "˙"
    assert part.letters
    assert part.zhuyin
    assert part.zhuyin.startswith("˙")
    assert "˙" not in (part.letters or "")


def test_zhuyin_other_tones_stay_beside_letters() -> None:
    parts = to_zhuyin_parts("好")
    part = next(part for part in parts if part.text == "好")
    assert part.letters
    if part.tone:
        assert part.tone in {"ˊ", "ˇ", "ˋ"}
        assert part.zhuyin == f"{part.letters}{part.tone}"


def test_zhuyin_does_not_treat_markup_as_html() -> None:
    parts = to_zhuyin_parts("<script>alert(1)</script>安全")
    joined = "".join(part.text for part in parts)
    assert "<script>" in joined
    assert any(part.text == "安" and part.zhuyin for part in parts)
