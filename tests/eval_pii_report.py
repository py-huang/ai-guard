"""Print tw-PII-bench misses so we tune rules, not dictionaries.

  .venv/bin/python -m tests.eval_pii_report
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from safety_gateway.pii.analyzer import build_analyzer_engine
from tests.tw_pii_bench import GOLD_TO_OURS

_FIXTURE = Path(__file__).parent / "fixtures" / "tw_pii_bench" / "short.jsonl"


def main() -> None:
    rows = [json.loads(line) for line in _FIXTURE.read_text(encoding="utf-8").splitlines() if line]
    engine = build_analyzer_engine()
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"gold": 0, "hit": 0})
    misses: dict[str, list[str]] = defaultdict(list)

    for row in rows:
        if row.get("is_negative"):
            continue
        hits = engine.analyze(text=row["text"], language="zh")
        for span in row.get("spans") or []:
            label = span["label"]
            ours = GOLD_TO_OURS.get(label)
            if not ours:
                continue
            stats[label]["gold"] += 1
            found = any(
                hit.entity_type in ours
                and not (hit.end <= span["start"] or hit.start >= span["end"])
                for hit in hits
            )
            if found:
                stats[label]["hit"] += 1
            elif len(misses[label]) < 5:
                misses[label].append(f"{span['text']!r} ← {row['text'][:80]}")

    print("label                  hit/gold  recall")
    for label, counts in sorted(stats.items()):
        gold, hit = counts["gold"], counts["hit"]
        print(f"{label:22} {hit:3}/{gold:<3}   {hit / gold if gold else 0:.0%}")
    print("\nmiss samples (max 5 / label)")
    for label, samples in sorted(misses.items()):
        print(f"\n[{label}]")
        for line in samples:
            print(f"  {line}")


if __name__ == "__main__":
    main()
