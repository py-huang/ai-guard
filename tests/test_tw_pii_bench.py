"""Regression against lianghsun/tw-PII-bench (short split, Apache-2.0, synthetic).

Source: https://huggingface.co/datasets/lianghsun/tw-PII-bench
Not a production lookup. Gold IDs may fail checksum; we still require format catch
when our recognizer does not require checksum, and checksum-valid ones for TW_ID.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from safety_gateway.pii.analyzer import build_analyzer_engine
from tests.tw_pii_bench import CORE_GOLD, GOLD_TO_OURS

_FIXTURE = Path(__file__).parent / "fixtures" / "tw_pii_bench" / "short.jsonl"


def _rows() -> list[dict]:
    return [json.loads(line) for line in _FIXTURE.read_text(encoding="utf-8").splitlines() if line]


def _overlaps(gold_start: int, gold_end: int, pred_start: int, pred_end: int) -> bool:
    return not (pred_end <= gold_start or pred_start >= gold_end)


def _evaluate() -> dict[str, dict[str, int]]:
    engine = build_analyzer_engine()
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"gold": 0, "hit": 0})
    for row in _rows():
        if row.get("is_negative"):
            continue
        hits = engine.analyze(text=row["text"], language="zh")
        for span in row.get("spans") or []:
            label = span["label"]
            ours = GOLD_TO_OURS.get(label)
            if not ours:
                continue
            stats[label]["gold"] += 1
            if any(
                hit.entity_type in ours and _overlaps(span["start"], span["end"], hit.start, hit.end)
                for hit in hits
            ):
                stats[label]["hit"] += 1
    return stats


def test_tw_pii_bench_short_core_recall() -> None:
    stats = _evaluate()
    missed = []
    for label in sorted(CORE_GOLD):
        gold = stats[label]["gold"]
        hit = stats[label]["hit"]
        recall = hit / gold if gold else 0.0
        # Floors: catch most Taiwan chat PII; indigenous / bad-checksum IDs can miss.
        floor = {
            "private_phone": 0.95,
            "private_email": 0.95,
            "private_address": 0.95,
            "private_person": 0.95,
            "tw_national_id": 0.95,
        }[label]
        if recall < floor:
            missed.append(f"{label} recall={recall:.2f} ({hit}/{gold}) < {floor}")
    assert not missed, "\n".join(missed)


def test_tw_pii_bench_checksum_valid_demo_id() -> None:
    engine = build_analyzer_engine()
    text = "我的身分證是 A123456789，電話 0912-345-678"
    types = {hit.entity_type for hit in engine.analyze(text=text, language="zh")}
    assert "TW_ID" in types
    assert "PHONE_NUMBER" in types
