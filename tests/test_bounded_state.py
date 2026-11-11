"""Memory that holds children's PII must be bounded and forgettable."""

from __future__ import annotations

import pytest

from safety_gateway.audit.memory import AuditEvent, InMemoryAuditLog
from safety_gateway.vault.memory import InMemorySessionVault


class _Clock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now


def test_vault_forgets_idle_sessions_after_ttl() -> None:
    clock = _Clock()
    vault = InMemorySessionVault(ttl_seconds=60, clock=clock)
    token = vault.get_or_create_token("s1", "PERSON", "王小明")
    assert vault.resolve_token("s1", token) == "王小明"

    clock.now += 61
    assert vault.resolve_token("s1", token) is None
    assert vault.deanonymize_text("s1", f"你好 {token}") == f"你好 {token}"
    assert vault.session_count == 0


def test_vault_activity_keeps_a_session_alive() -> None:
    clock = _Clock()
    vault = InMemorySessionVault(ttl_seconds=60, clock=clock)
    token = vault.get_or_create_token("s1", "PERSON", "王小明")
    clock.now += 40
    assert vault.resolve_token("s1", token) == "王小明"  # touch
    clock.now += 40
    assert vault.resolve_token("s1", token) == "王小明"


def test_vault_evicts_least_recently_used_session() -> None:
    vault = InMemorySessionVault(max_sessions=2)
    vault.get_or_create_token("a", "PERSON", "甲")
    vault.get_or_create_token("b", "PERSON", "乙")
    vault.list_mappings("a")  # a is now more recent than b
    vault.get_or_create_token("c", "PERSON", "丙")

    assert vault.list_mappings("b") == {}
    assert vault.list_mappings("a") != {}
    assert vault.list_mappings("c") != {}
    assert vault.session_count == 2


def test_vault_tokens_stay_stable_inside_a_session() -> None:
    vault = InMemorySessionVault(ttl_seconds=60, max_sessions=10)
    first = vault.get_or_create_token("s", "PERSON", "王小明")
    again = vault.get_or_create_token("s", "PERSON", "王小明")
    other = vault.get_or_create_token("s", "PERSON", "李小華")
    assert first == again == "<PERSON_1>"
    assert other == "<PERSON_2>"


def test_vault_rejects_nonsense_limits() -> None:
    with pytest.raises(ValueError):
        InMemorySessionVault(ttl_seconds=0)
    with pytest.raises(ValueError):
        InMemorySessionVault(max_sessions=0)


def _event(session_id: str, index: int) -> AuditEvent:
    return AuditEvent(
        event_id=f"{session_id}-{index}",
        at="2026-01-01T00:00:00+00:00",
        session_id=session_id,
        direction="inbound",
        sanitized_text="x",
        entity_types=[],
        blocked=False,
    )


def test_audit_cap_is_per_session_so_one_family_cannot_evict_another() -> None:
    log = InMemoryAuditLog(max_events=3, max_sessions=10)
    log.append(_event("quiet", 0))
    for index in range(50):
        log.append(_event("noisy", index))

    assert [event.event_id for event in log.list_session("quiet")] == ["quiet-0"]
    assert [event.event_id for event in log.list_session("noisy")] == [
        "noisy-47",
        "noisy-48",
        "noisy-49",
    ]


def test_audit_bounds_total_sessions() -> None:
    log = InMemoryAuditLog(max_events=5, max_sessions=2)
    for name in ("a", "b", "c"):
        log.append(_event(name, 0))
    assert log.session_count == 2
    assert log.list_session("a") == []


def test_audit_clear_session_and_all() -> None:
    log = InMemoryAuditLog()
    log.append(_event("a", 0))
    log.append(_event("b", 0))
    log.clear_session("a")
    assert log.list_session("a") == []
    log.clear_all()
    assert log.session_count == 0
