"""Reuse a vaulted full name when the child later writes 小明 / 陳同學."""

from __future__ import annotations

from presidio_analyzer import RecognizerResult

from safety_gateway.pii.taiwan_names import aliases_for_person
from safety_gateway.vault.base import BaseSessionVault


def person_originals(vault: BaseSessionVault, session_id: str, extra: list[str] | None = None) -> list[str]:
    found = list(extra or [])
    for token, original in vault.list_mappings(session_id).items():
        if token.startswith("<PERSON_") and original not in found:
            found.append(original)
    return found


def register_person_aliases(vault: BaseSessionVault, session_id: str, full_name: str) -> None:
    for alias in aliases_for_person(full_name):
        vault.alias_value(session_id, "PERSON", alias, full_name)


def alias_hits(text: str, vault: BaseSessionVault, session_id: str, extra_names: list[str]) -> list[RecognizerResult]:
    names = person_originals(vault, session_id, extra_names)
    for name in names:
        register_person_aliases(vault, session_id, name)

    needles: list[tuple[str, str]] = []
    for name in names:
        for alias in aliases_for_person(name):
            needles.append((alias, name))
    needles.sort(key=lambda item: len(item[0]), reverse=True)

    used: list[tuple[int, int]] = []
    results: list[RecognizerResult] = []
    for alias, canonical in needles:
        start = 0
        while True:
            index = text.find(alias, start)
            if index < 0:
                break
            end = index + len(alias)
            start = index + 1
            if any(not (end <= left or index >= right) for left, right in used):
                continue
            used.append((index, end))
            vault.alias_value(session_id, "PERSON", text[index:end], canonical)
            results.append(
                RecognizerResult(entity_type="PERSON", start=index, end=end, score=0.88)
            )
    return results
