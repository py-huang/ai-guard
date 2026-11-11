#!/usr/bin/env python3
"""PII recall on synthetic Taiwanese data, broken down by kind and by noise style.

  .venv/bin/python scripts/eval_pii_synth.py [--n 150] [--seed 1] [--show 5]
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from eval_corpus import wilson  # noqa: E402
from safety_gateway.gateway import AISafetyGateway  # noqa: E402
from tests.synth_pii import generate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=150, help="samples per kind")
    parser.add_argument("--seed", type=int, default=20260511)
    parser.add_argument("--show", type=int, default=4, help="leaked examples to print per kind")
    parser.add_argument("--min-recall", type=float, default=0.0, help="exit 1 if overall recall is lower")
    args = parser.parse_args()

    gateway = AISafetyGateway()
    by_kind: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    by_noise: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    leaks: dict[str, list[str]] = defaultdict(list)

    for index, sample in enumerate(generate(args.n, args.seed)):
        result = gateway.sanitize_text(f"synth-{index}", sample.text)
        protected = result.blocked or not any(secret and secret in result.processed_text for secret in sample.secrets)
        for bucket in (by_kind[sample.kind], by_noise[(sample.kind, sample.noise)]):
            bucket[0] += 1
            bucket[1] += int(protected)
        if not protected:
            leaks[sample.kind].append(f"[{sample.noise}] {sample.text}  ->  {result.processed_text}")

    total = sum(v[0] for v in by_kind.values())
    safe = sum(v[1] for v in by_kind.values())
    print(f"synthetic PII, {args.n}/kind, seed {args.seed}   (protected = secret absent from output)\n")
    for kind, (n, ok) in by_kind.items():
        lo, hi = wilson(ok, n)
        print(f"{kind:9} {ok:4}/{n:<4} {ok / n:6.1%}  [{lo:.1%}-{hi:.1%}]")
        weak = [(noise, v) for (k, noise), v in by_noise.items() if k == kind and v[1] < v[0]]
        for noise, (nn, oo) in sorted(weak, key=lambda item: item[1][1] / item[1][0]):
            print(f"            weak: {noise:13} {oo}/{nn}")
    print(f"\nOVERALL {safe}/{total} = {safe / total:.1%}")
    for kind, items in leaks.items():
        print(f"\n--- {kind}: leaked examples ---")
        for line in items[: args.show]:
            print("  ", line)
    return 0 if safe / total >= args.min_recall else 1


if __name__ == "__main__":
    sys.exit(main())
