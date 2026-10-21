from __future__ import annotations

from safety_gateway.vault.memory import InMemorySessionVault


def test_tokens_are_stable_within_session() -> None:
    vault = InMemorySessionVault()
    first = vault.get_or_create_token("s1", "PERSON", "王小明")
    second = vault.get_or_create_token("s1", "PERSON", "王小明")
    other = vault.get_or_create_token("s1", "PERSON", "陳小華")
    assert first == "<PERSON_1>"
    assert first == second
    assert other == "<PERSON_2>"


def test_alias_shares_the_same_person_token() -> None:
    vault = InMemorySessionVault()
    token = vault.get_or_create_token("s1", "PERSON", "陳小明")
    alias = vault.alias_value("s1", "PERSON", "小明", "陳小明")
    again = vault.get_or_create_token("s1", "PERSON", "小明")
    assert token == alias == again == "<PERSON_1>"


def test_sessions_are_isolated() -> None:
    vault = InMemorySessionVault()
    vault.get_or_create_token("s1", "SCHOOL", "中山國小")
    other_session = vault.get_or_create_token("s2", "SCHOOL", "中山國小")
    assert other_session == "<SCHOOL_1>"
    assert vault.deanonymize_text("s2", "去 <SCHOOL_1> 上課") == "去 中山國小 上課"
    assert vault.resolve_token("s1", "<SCHOOL_1>") == "中山國小"
