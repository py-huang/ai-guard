#!/usr/bin/env python3
"""False-positive rate of PERSON detection on ordinary (non-name-bearing) text, plus name recall.

Public benign sets contain very few real full names, so a PERSON hit there is almost always a
false alarm (an over-masked noun, place, brand, or title). Recall is checked separately on the
1000 eval-only names so that tightening the filter cannot silently stop masking real names.

  .venv/bin/python scripts/eval_pii_names.py [--split dev|test] [--show 25]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_corpus import wilson  # noqa: E402
from safety_gateway.gateway import AISafetyGateway  # noqa: E402
from safety_gateway.pii.name_eval_set import TOP_1000_FULL_NAMES  # noqa: E402

UNIFIED = ROOT / ".cache" / "eval-corpus" / "unified.jsonl"
BENIGN_SETS = ("taiwanchat_benign", "cold_neutral", "benign_instruction", "reverse_protective")
RECALL_FRAMES = ("我是{}", "同學{}今天沒來", "請幫我寫信給{}", "{}說明天要考試", "我的導師是{}老師")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", default="dev", choices=["dev", "test"])
    parser.add_argument("--show", type=int, default=25)
    parser.add_argument("--max-fp", type=float, default=1.0, help="exit 1 if the FP rate is higher")
    parser.add_argument("--min-recall", type=float, default=0.0, help="exit 1 if name recall is lower")
    args = parser.parse_args()

    gateway = AISafetyGateway()
    rows = [json.loads(line) for line in UNIFIED.read_text(encoding="utf-8").split("\n") if line]
    rows = [r for r in rows if r["set"] in BENIGN_SETS and r["split"] == args.split]

    spans: Counter[str] = Counter()
    flagged: dict[str, list[int]] = {name: [0, 0] for name in BENIGN_SETS}
    for index, row in enumerate(rows):
        result = gateway.sanitize_text(f"fp-{index}", row["text"])
        names = [e for e in result.entities if "PERSON" in str(e.entity_type)]
        flagged[row["set"]][1] += 1
        if names:
            flagged[row["set"]][0] += 1
            for entity in names:
                spans[row["text"][entity.start : entity.end]] += 1
    total = sum(v[1] for v in flagged.values())
    hit = sum(v[0] for v in flagged.values())
    lo, hi = wilson(hit, total)
    print(f"benign PERSON false positives ({args.split}, {total} sentences)")
    for name, (bad, n) in flagged.items():
        print(f"  {name:20} {bad:4}/{n:<5} {bad / max(n, 1):6.1%}")
    print(f"  OVERALL              {hit:4}/{total:<5} {hit / total:6.1%}  [{lo:.1%}-{hi:.1%}]")
    print("  most frequent flagged spans:", ", ".join(f"{s}×{c}" for s, c in spans.most_common(args.show)))

    protected = 0
    count = 0
    missed: list[str] = []
    for index, name in enumerate(TOP_1000_FULL_NAMES[::5]):
        frame = RECALL_FRAMES[index % len(RECALL_FRAMES)]
        text = frame.format(name)
        result = gateway.sanitize_text(f"nr-{index}", text)
        count += 1
        if name not in result.processed_text:
            protected += 1
        elif len(missed) < 8:
            missed.append(text)
    rlo, rhi = wilson(protected, count)
    print(f"\nname recall on eval-only names: {protected}/{count} = {protected / count:.1%} [{rlo:.1%}-{rhi:.1%}]")
    for text in missed:
        print("   leaked:", text)
    ok = hit / total <= args.max_fp and protected / count >= args.min_recall
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
