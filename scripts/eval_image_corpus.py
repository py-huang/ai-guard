#!/usr/bin/env python3
"""Run the local image forbid pipeline on the Wikimedia corpus."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.image_forbid import classify_forbidden_image
from safety_gateway.pii.ocr import ocr_lines

ROOT = Path(__file__).resolve().parents[1]


def _load_env() -> None:
    import os

    os.environ.setdefault("IMAGE_FORBID_VISION", "auto")
    os.environ.setdefault("IMAGE_FORBID_CACHE", str(ROOT / "tests" / "fixtures" / "image-corpus" / ".vision-cache"))
    for name in (".env.local", ".env"):
        path = ROOT / name
        if not path.is_file():
            continue
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
CORPUS = ROOT / "tests" / "fixtures" / "image-corpus"
EXPECTED = {
    "01-body": "body",
    "02-violence": "violence",
    "03-voyeur": "voyeur",
    "04-document": "document",
    "05-other": "other",
}


def main() -> None:
    _load_env()
    gateway = AISafetyGateway()
    rows: list[dict[str, str]] = []
    for category, expected in EXPECTED.items():
        folder = CORPUS / category
        files = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp"})
        for path in files:
            ocr = " ".join(ocr_lines(path.read_bytes()))
            result = gateway.redact_image("corpus", path.read_bytes())
            predicted = result.block_reason or classify_forbidden_image(ocr, result.detected_entities) or ""
            hit = predicted == expected or (expected == "document" and predicted in {"document", "sensitive"})
            rows.append(
                {
                    "category": category,
                    "expected": expected,
                    "file": path.name,
                    "blocked": "yes" if result.blocked else "no",
                    "predicted": predicted or "none",
                    "entities": ",".join(result.detected_entities),
                    "ocr_preview": ocr[:180].replace("\n", " "),
                    "success": "yes" if hit and result.blocked else "no",
                }
            )
            print(f"{category}/{path.name} blocked={result.blocked} pred={predicted or 'none'} ok={rows[-1]['success']}")

    (CORPUS / "eval.csv").write_text(
        _csv(rows),
        encoding="utf-8",
    )
    summary = _summary(rows)
    (CORPUS / "EVAL.md").write_text(summary, encoding="utf-8")
    print(summary)


def _csv(rows: list[dict[str, str]]) -> str:
    if not rows:
        return ""
    output = []
    writer_keys = list(rows[0].keys())
    lines = [",".join(writer_keys)]
    for row in rows:
        packed = []
        for key in writer_keys:
            value = row[key].replace('"', "'")
            packed.append(f'"{value}"')
        lines.append(",".join(packed))
    return "\n".join(lines) + "\n"


def _summary(rows: list[dict[str, str]]) -> str:
    lines = ["# Image corpus evaluation", "", "Source: Wikimedia Commons (CC / public files). Not porn sites, gore boards, or real Taiwan IDs.", ""]
    lines.append("| category | n | success | fail |")
    lines.append("| --- | --- | --- | --- |")
    for category in EXPECTED:
        group = [row for row in rows if row["category"] == category]
        ok = sum(1 for row in group if row["success"] == "yes")
        lines.append(f"| {category} | {len(group)} | {ok} | {len(group) - ok} |")
    lines += ["", "## Failures", ""]
    for row in rows:
        if row["success"] != "yes":
            lines.append(f"- `{row['category']}/{row['file']}` expected `{row['expected']}` got `{row['predicted']}` blocked={row['blocked']} ocr=`{row['ocr_preview'][:80]}`")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
