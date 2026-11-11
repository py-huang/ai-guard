#!/usr/bin/env python3
"""Large-scale evaluation of the content-safety layer against public, licensed datasets.

  .venv/bin/python scripts/eval_corpus.py fetch     # download raw files into .cache/eval-corpus/raw
  .venv/bin/python scripts/eval_corpus.py build     # convert to Traditional Chinese + unified jsonl
  .venv/bin/python scripts/eval_corpus.py run       # evaluate (add --split dev|test, --engine rules|model|combined)

Why public datasets and not scraping: they are labelled, licensed, reproducible, and nobody
has to browse harmful sites to build them. Raw data and reports stay under ``.cache/``
(git-ignored); only this script and its methodology are committed.

Method (important, so the numbers stay honest):
  * Each source is used only for what its labels can actually support. Sets whose label is
    "the topic is sensitive" rather than "a child bot must refuse this" are INFORMATIONAL:
    we report a block rate and print samples to review, but never call it a pass/fail.
  * Texts are split deterministically into dev/test by hash. Tune the catalog on ``dev``,
    quote ``test``. Looking at test misses and then fixing them turns test into dev.
  * Rates carry a 95% Wilson interval so a 30-sample result is not mistaken for a fact.
  * ``build`` also writes ``corpus.jsonl`` (uncapped) with a ``part`` of train/val/test for
    training a model. ``test`` is the same odd-hash half as the ``test`` split, and it is never
    trained on. Everything here stays under ``.cache/`` and is never committed.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
CACHE = ROOT / ".cache" / "eval-corpus"
RAW = CACHE / "raw"
UNIFIED = CACHE / "unified.jsonl"
CORPUS = CACHE / "corpus.jsonl"
REPORTS = CACHE / "reports"
MODEL_DIR = Path(os.environ.get("EVAL_MODEL_DIR") or CACHE.parent / "models" / "content_safety")
CHALLENGE = ROOT / "tests" / "fixtures" / "content_safety_challenge.jsonl"
# Written after the model was tuned and never used for tuning: quote it, do not fit to it.
HOLDOUT = ROOT / "tests" / "fixtures" / "content_safety_holdout.jsonl"
HOLDOUT2 = ROOT / "tests" / "fixtures" / "content_safety_holdout2.jsonl"

SAFETY_PROMPTS = "https://raw.githubusercontent.com/thu-coai/Safety-Prompts/main/"
COLD = "https://raw.githubusercontent.com/thu-coai/COLDataset/main/COLDataset/"
SOURCES: dict[str, tuple[str, str]] = {
    "typical_safety_scenarios.json": (SAFETY_PROMPTS + "typical_safety_scenarios.json", "Apache-2.0 thu-coai/Safety-Prompts"),
    "instruction_attack_scenarios.json": (SAFETY_PROMPTS + "instruction_attack_scenarios.json", "Apache-2.0 thu-coai/Safety-Prompts"),
    "cold_train.csv": (COLD + "train.csv", "thu-coai/COLDataset (research use)"),
    "cold_dev.csv": (COLD + "dev.csv", "thu-coai/COLDataset (research use)"),
    "cold_test.csv": (COLD + "test.csv", "thu-coai/COLDataset (research use)"),
}

# name -> (expected behaviour, authoritative?)
#   block  : a child-safe assistant must refuse/redirect
#   allow  : must pass through untouched
#   review : block rate is reported; samples are for a human to read
SETS: dict[str, tuple[str, bool]] = {
    "unsafe_instruction": ("block", True),
    "goal_hijacking": ("block", True),
    "insult": ("block", True),
    "cold_neutral": ("allow", True),
    "taiwanchat_benign": ("allow", True),
    "injection_en": ("block", True),
    "benign_en": ("allow", True),
    # NOTE: Safety-Prompts' Reverse_Exposure is a MIX of genuine attacks ("how do I evade tax")
    # and protective questions, so it is NOT a clean negative set. It is informational only and
    # is never used for training.
    "reverse_exposure": ("review", False),
    "reverse_protective": ("allow", False),
    # COLD's own label is offensive vs not, in the same distribution as cold_neutral.
    "cold_offensive": ("block", True),
    # Short, ordinary, imperative-style requests: the negatives that stop a model learning
    # "imperative sentence == unsafe" from the Safety-Prompts attack sets.
    "benign_instruction": ("allow", True),
    # Public English red-team behaviours (AdvBench, HarmBench, JailbreakBench, XSTest-unsafe) and the
    # matching "looks dangerous, is fine" contrasts (XSTest-safe, JBB-benign). A multilingual encoder
    # carries the intent across languages, so these teach "how do I make / get / hide X" in general.
    # Adult-flavoured and English: they train the model but are not part of the scored macro.
    "redteam_en": ("block", False),
    "contrast_safe_en": ("allow", False),
    "mental_health": ("review", False),
    "physical_harm": ("review", False),
    "role_play": ("review", False),
    "ethics": ("review", False),
}
MAX_PER_SET = 2_000

# Reverse_Exposure asks what one should AVOID ("我應該避免哪些不當言論？"). Most are protective;
# a minority smuggle in genuinely harmful asks. Rows with an explicit protective cue become
# ``reverse_protective``: same style as the attack prompts but harmless, which is exactly what a
# classifier needs to stop reading "imperative / how-to" as "attack". Weakly labelled by this
# cue list, so it trains the model and is reported, but is not an authoritative test set.
_PROTECTIVE_CUE = re.compile(
    "避免|防止|預防|遠離|保護自己|保護好|如何保護|不應該|不應當|不該|不要去|不希望|合法|正確的?方式|正當|"
    "識別|辨別|辨識|防範|應對|不會去|不想去|尊重|我們應該|我不會|不會做|不會嘗試|規範|遵守|守法"
)


HF_ROWS = "https://datasets-server.huggingface.co/rows"
# (dataset, split, rows wanted, license note). Rows are sampled from spread-out offsets with a
# fixed seed, because the head of a dataset is rarely representative of the rest.
HF_SOURCES: dict[str, tuple[str, str, int, str]] = {
    "hf_taiwanchat.jsonl": ("yentinglin/TaiwanChat", "train", 3_000, "Apache-2.0 yentinglin/TaiwanChat"),
    "hf_prompt_injections.jsonl": ("deepset/prompt-injections", "train", 546, "Apache-2.0 deepset/prompt-injections"),
    "hf_taiwanchat_extra.jsonl": ("yentinglin/TaiwanChat", "train", 6_000, "Apache-2.0 yentinglin/TaiwanChat"),
}
# Whole-file download is far more reliable than 100+ paged API calls for this one.
ALPACA_ZH = "https://huggingface.co/datasets/shibing624/alpaca-zh/resolve/main/alpaca_gpt4_data_zh.json"
ALPACA_ROWS = 12_000
JAILBREAK_CSV = "https://huggingface.co/datasets/jackhhao/jailbreak-classification/resolve/main/default/jailbreak_dataset_full.csv"
# Sources that need their own sampling seed so they do not re-draw an earlier file's pages.
HF_SEEDS: dict[str, int] = {"hf_taiwanchat_extra.jsonl": 7}


def _hf_json(params: dict[str, str | int]) -> dict:
    import urllib.parse

    import urllib.error

    url = f"{HF_ROWS}?{urllib.parse.urlencode(params)}"
    for attempt in range(6):
        try:
            with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - fixed https host
                time.sleep(0.4)  # be polite to a free public API
                return json.loads(response.read())
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == 5:
                raise
            time.sleep(2 ** attempt * 2)
        except (TimeoutError, urllib.error.URLError, ConnectionError):
            if attempt == 5:
                raise
            time.sleep(2 ** attempt * 2)
    raise RuntimeError("unreachable")


def fetch_hf() -> dict[str, dict]:
    import random

    manifest: dict[str, dict] = {}
    for name, (dataset, split, wanted, license_note) in HF_SOURCES.items():
        target = RAW / name
        if not target.exists():
            print(f"downloading {dataset} ...")
            base = {"dataset": dataset, "config": "default", "split": split, "length": 100}
            total = _hf_json({**base, "offset": 0})["num_rows_total"]
            rng = random.Random(HF_SEEDS.get(name, 20260511))
            pages = max(1, math.ceil(wanted / 100))
            if total <= wanted:  # small dataset: take everything
                offsets = list(range(0, total, 100))
            else:
                offsets = sorted(rng.sample(range(0, total - 100), pages))
            rows = []
            for offset in offsets:
                rows.extend(item["row"] for item in _hf_json({**base, "offset": offset})["rows"])
            target.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
        manifest[name] = {"dataset": dataset, "license": license_note, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    return manifest


def fetch_alpaca() -> dict[str, dict]:
    import random

    target = RAW / "hf_alpaca_zh.jsonl"
    if not target.exists():
        print("downloading shibing624/alpaca-zh ...")
        with urllib.request.urlopen(ALPACA_ZH, timeout=300) as response:  # noqa: S310 - fixed https URL
            records = json.loads(response.read())
        usable = [r for r in records if not r.get("input") and 4 <= len(r["instruction"]) <= 200]
        random.Random(11).shuffle(usable)
        rows = [{"instruction": r["instruction"]} for r in usable[:ALPACA_ROWS]]
        target.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows), encoding="utf-8")
    return {"hf_alpaca_zh.jsonl": {"dataset": "shibing624/alpaca-zh", "license": "CC-BY-4.0",
                                  "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}}


def fetch_jailbreak() -> dict[str, dict]:
    target = RAW / "hf_jailbreak.csv"
    if not target.exists():
        print("downloading jackhhao/jailbreak-classification ...")
        with urllib.request.urlopen(JAILBREAK_CSV, timeout=300) as response:  # noqa: S310 - fixed https URL
            target.write_bytes(response.read())
    return {"hf_jailbreak.csv": {"dataset": "jackhhao/jailbreak-classification", "license": "Apache-2.0",
                                "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}}


REDTEAM_SOURCES: dict[str, tuple[str, str]] = {
    "advbench.csv": ("https://raw.githubusercontent.com/llm-attacks/llm-attacks/main/data/advbench/harmful_behaviors.csv",
                     "MIT llm-attacks/AdvBench"),
    "xstest.csv": ("https://raw.githubusercontent.com/paul-rottger/xstest/main/xstest_prompts.csv", "CC-BY-4.0 XSTest"),
    "harmbench.csv": ("https://raw.githubusercontent.com/centerforaisafety/HarmBench/main/data/behavior_datasets/"
                      "harmbench_behaviors_text_all.csv", "MIT HarmBench"),
    "jbb_harmful.csv": ("https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/resolve/main/data/harmful-behaviors.csv",
                        "MIT JailbreakBench"),
    "jbb_benign.csv": ("https://huggingface.co/datasets/JailbreakBench/JBB-Behaviors/resolve/main/data/benign-behaviors.csv",
                       "MIT JailbreakBench"),
}


def fetch_redteam() -> dict[str, dict]:
    manifest = {}
    for name, (url, license_note) in REDTEAM_SOURCES.items():
        target = RAW / name
        if not target.exists():
            print(f"downloading {name} ...")
            with urllib.request.urlopen(url, timeout=180) as response:  # noqa: S310 - fixed https URLs
                target.write_bytes(response.read())
        manifest[name] = {"url": url, "license": license_note, "sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    return manifest


def _csv_rows(name: str) -> list[dict[str, str]]:
    path = RAW / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def redteam_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    rows += [{"set": "redteam_en", "text": r["goal"]} for r in _csv_rows("advbench.csv")]
    rows += [{"set": "redteam_en", "text": r["Behavior"]} for r in _csv_rows("harmbench.csv")
             if r.get("FunctionalCategory") == "standard"]
    rows += [{"set": "redteam_en", "text": r["Goal"]} for r in _csv_rows("jbb_harmful.csv")]
    for r in _csv_rows("xstest.csv"):
        rows.append({"set": "contrast_safe_en" if r["label"] == "safe" else "redteam_en", "text": r["prompt"]})
    rows += [{"set": "contrast_safe_en", "text": r["Goal"]} for r in _csv_rows("jbb_benign.csv")]
    return rows


def fetch() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for name, (url, license_note) in SOURCES.items():
        target = RAW / name
        if not target.exists():
            print(f"downloading {name} ...")
            with urllib.request.urlopen(url, timeout=180) as response:  # noqa: S310 - fixed https URLs
                target.write_bytes(response.read())
        manifest[name] = {
            "url": url,
            "license": license_note,
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "bytes": target.stat().st_size,
        }
    manifest.update(fetch_hf())
    manifest.update(fetch_alpaca())
    manifest.update(fetch_jailbreak())
    manifest.update(fetch_redteam())
    (RAW / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"ok: {len(manifest)} files in {RAW}")


def _split(text: str) -> str:
    return "dev" if int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16) % 2 == 0 else "test"


def _looks_german(text: str) -> bool:
    lowered = f" {text.lower()} "
    markers = (" und ", " der ", " die ", " das ", " ich ", " nicht ", " ist ", " ein ", " zu ", " mit ", " für ", " wie ")
    return any(c in text for c in "äöüß") or sum(m in lowered for m in markers) >= 2


def _read_lines(path: Path) -> list[str]:
    """Missing optional files are skipped; ``split("\\n")`` because splitlines() also splits on U+2028."""
    if not path.exists():
        return []
    return [line for line in path.read_text(encoding="utf-8").split("\n") if line]


def _part(text: str) -> str:
    """train/val/test. ``test`` is exactly the odd-hash half (same rows as split == "test")."""
    digest = int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16)
    if digest % 2:
        return "test"
    return "val" if (digest >> 1) % 5 == 0 else "train"


def build() -> None:
    # Optional dependency: `pip install opencc-python-reimplemented`, or into .cache/pylib.
    sys.path.append(str(CACHE.parent / "pylib"))
    from opencc import OpenCC

    to_tw = OpenCC("s2twp")  # Simplified -> Traditional with Taiwan phrasing
    rows: list[dict[str, str]] = []

    typical = json.loads((RAW / "typical_safety_scenarios.json").read_text(encoding="utf-8"))
    attack = json.loads((RAW / "instruction_attack_scenarios.json").read_text(encoding="utf-8"))
    mapping = [
        ("unsafe_instruction", attack["Unsafe_Instruction_Topic"]),
        ("goal_hijacking", attack["Goal_Hijacking"]),
        ("insult", typical["Insult"]),
        ("reverse_exposure", attack["Reverse_Exposure"]),
        ("mental_health", typical["Mental_Health"]),
        ("physical_harm", typical["Physical_Harm"]),
        ("role_play", attack["Role_Play_Instruction"]),
        ("ethics", typical["Ethics_And_Morality"]),
    ]
    for name, items in mapping:
        for item in items:
            rows.append({"set": name, "text": item["prompt"]})

    for part in ("cold_train.csv", "cold_dev.csv", "cold_test.csv"):
        with (RAW / part).open(encoding="utf-8-sig", newline="") as handle:
            for record in csv.DictReader(handle):
                name = "cold_offensive" if record["label"] == "1" else "cold_neutral"
                rows.append({"set": name, "text": record["TEXT"]})

    for line in (RAW / "hf_taiwanchat.jsonl").read_text(encoding="utf-8").split("\n"):
        if not line:
            continue
        record = json.loads(line)
        first = next((m["content"] for m in record.get("messages", []) if m["role"] == "user"), "")
        rows.append({"set": "taiwanchat_benign", "text": first.strip()})
    for line in (RAW / "hf_prompt_injections.jsonl").read_text(encoding="utf-8").split("\n"):
        if not line:
            continue
        record = json.loads(line)
        if _looks_german(record["text"]):
            continue  # the dataset mixes in German; our scope is zh-TW and English
        rows.append({"set": "injection_en" if record["label"] == 1 else "benign_en", "text": record["text"]})

    for line in _read_lines(RAW / "hf_taiwanchat_extra.jsonl"):
        record = json.loads(line)
        first = next((m["content"] for m in record.get("messages", []) if m["role"] == "user"), "")
        if len(first.strip()) <= 200:
            rows.append({"set": "benign_instruction", "text": first.strip()})
    for line in _read_lines(RAW / "hf_alpaca_zh.jsonl"):
        record = json.loads(line)
        if not record.get("input") and len(record["instruction"].strip()) <= 200:
            rows.append({"set": "benign_instruction", "text": record["instruction"].strip()})

    jailbreak = RAW / "hf_jailbreak.csv"
    if jailbreak.exists():
        with jailbreak.open(encoding="utf-8", newline="") as handle:
            for record in csv.DictReader(handle):
                # Long DAN-style prompts: the opening is what a child-sized filter would see.
                text = record["prompt"].strip()[:300]
                rows.append({"set": "injection_en" if record["type"] == "jailbreak" else "benign_en", "text": text})

    rows.extend(redteam_rows())

    seen: set[str] = set()
    per_set: Counter[str] = Counter()
    out: list[dict[str, str]] = []
    for row in rows:
        text = to_tw.convert(row["text"].strip())
        # Short, single-turn child-sized messages only: the gateway caps input at 4000 chars
        # and children do not paste essays.
        if not 4 <= len(text) <= 400 or text in seen:
            continue
        seen.add(text)
        name = row["set"]
        if name == "reverse_exposure" and _PROTECTIVE_CUE.search(text):
            name = "reverse_protective"
        out.append({"set": name, "text": text, "split": _split(text), "part": _part(text)})
    # Deterministic cap per set (hash order, not file order, so no category-of-origin bias).
    out.sort(key=lambda r: hashlib.sha1(r["text"].encode()).hexdigest())
    capped = []
    for row in out:
        if per_set[row["set"]] < MAX_PER_SET:
            per_set[row["set"]] += 1
            capped.append(row)
    CORPUS.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out), encoding="utf-8")
    UNIFIED.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in capped), encoding="utf-8")
    print(f"wrote {len(out)} rows -> {CORPUS}  (train/val/test, uncapped, for training)")
    print(f"wrote {len(capped)} rows -> {UNIFIED}  (capped, for evaluation)")
    for name, count in sorted(per_set.items()):
        print(f"  {name:20} {count}")


def wilson(hits: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return 0.0, 0.0
    p = hits / total
    denom = 1 + z * z / total
    centre = (p + z * z / (2 * total)) / denom
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / denom
    return max(0.0, centre - half), min(1.0, centre + half)


def make_classifier(engine: str):
    """``text -> (category, why) | None`` for the chosen engine."""
    from safety_gateway.steps.content_model import load_if_present
    from safety_gateway.steps.content_safety import ContentSafetyStep

    model = load_if_present(MODEL_DIR) if engine != "rules" else None
    if engine != "rules" and model is None:
        raise SystemExit(f"no trained model in {MODEL_DIR}; run scripts/train_content_model.py")
    if engine == "model":

        def classify_model(text: str):
            verdict = model.predict(text)
            return (verdict.category, f"ml:{verdict.label}") if verdict.blocked else None

        return classify_model
    step = ContentSafetyStep(model=model)

    def classify_step(text: str):
        match = step.classify(text)
        return None if match is None else (match.category, f"{match.category}:{match.phrase}")

    return classify_step


def accuracy_summary(stats: dict[str, dict[str, int]]) -> None:
    """One honest headline: per-set correct rate, averaged with every set weighing the same."""
    correct: dict[str, float] = {}
    pooled_hit = pooled_n = 0
    for name, (expect, authoritative) in SETS.items():
        entry = stats.get(name)
        if not authoritative or not entry or not entry["n"] or expect == "review":
            continue
        hit = entry["blocked"] if expect == "block" else entry["n"] - entry["blocked"]
        correct[name] = hit / entry["n"]
        pooled_hit += hit
        pooled_n += entry["n"]
    if not correct:
        return
    block = [v for k, v in correct.items() if SETS[k][0] == "block"]
    allow = [v for k, v in correct.items() if SETS[k][0] == "allow"]
    macro = sum(correct.values()) / len(correct)
    print(f"\ncorrect-judgement rate over authoritative sets (n={pooled_n}):")
    print(f"  macro (each set weighs the same)  {macro:6.1%}")
    print(f"  pooled accuracy                   {pooled_hit / pooled_n:6.1%}")
    print(f"  harmful caught (mean over sets)   {sum(block) / len(block):6.1%}")
    print(f"  harmless allowed (mean over sets) {sum(allow) / len(allow):6.1%}")
    print(f"  weakest set                       {min(correct, key=correct.get)} {min(correct.values()):.1%}")


def run_challenge(engine: str, path: Path = CHALLENGE) -> None:
    """Hand-written, source-independent sentences: do the numbers survive a different author?"""
    classify = make_classifier(engine)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").split("\n") if line]
    wrong: list[str] = []
    totals = {"block": [0, 0], "allow": [0, 0]}
    for row in rows:
        blocked = classify(row["text"]) is not None
        ok = blocked == (row["expect"] == "block")
        totals[row["expect"]][0] += int(ok)
        totals[row["expect"]][1] += 1
        if not ok:
            wrong.append(f"  {'MISSED ' if row['expect'] == 'block' else 'WRONGLY BLOCKED '}{row['text']}")
    hit = sum(v[0] for v in totals.values())
    print(f"\n{path.stem} ({len(rows)} hand-written sentences, engine={engine}):")
    print(f"  accuracy {hit / len(rows):.1%}   harmful caught {totals['block'][0]}/{totals['block'][1]}"
          f"   harmless allowed {totals['allow'][0]}/{totals['allow'][1]}")
    for line in wrong[:40]:
        print(line)


def run_synthetic(engine: str) -> None:
    """Sentences from template families the model never trained on (see tests/synth_content.py)."""
    from tests.synth_content import family_part, generate

    classify = make_classifier(engine)
    samples = [s for s in generate() if family_part(s.family) == "test"]
    by_label: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    wrong: list[str] = []
    for sample in samples:
        blocked = classify(sample.text) is not None
        ok = blocked == (sample.label != "allow")
        by_label[sample.label][0] += int(ok)
        by_label[sample.label][1] += 1
        if not ok:
            wrong.append(f"  [{sample.label}] {sample.text}")
    total_hit = sum(v[0] for v in by_label.values())
    print(f"\nheld-out template families ({len(samples)} generated sentences, engine={engine}): "
          f"accuracy {total_hit / len(samples):.1%}")
    for label, (hit, n) in sorted(by_label.items()):
        print(f"  {label:10} {hit}/{n}  {hit / n:.1%}")
    for line in wrong[:15]:
        print(line)


def run(split: str, show: int, engine: str = "rules", challenge: bool = False, synth: bool = False,
        holdout: bool = False, holdout2: bool = False) -> int:
    if holdout2:
        run_challenge(engine, HOLDOUT2)
        return 0
    if holdout:
        run_challenge(engine, HOLDOUT)
        return 0
    if synth:
        run_synthetic(engine)
        return 0
    if challenge:
        run_challenge(engine)
        return 0
    if not UNIFIED.exists():
        print("run `fetch` and `build` first")
        return 2
    classify = make_classifier(engine)
    stats: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "blocked": 0})
    flagged: dict[str, list[tuple[str, str]]] = defaultdict(list)
    missed: dict[str, list[str]] = defaultdict(list)
    phrases: dict[str, Counter[str]] = defaultdict(Counter)

    for line in UNIFIED.read_text(encoding="utf-8").split("\n"):
        if not line:
            continue
        row = json.loads(line)
        if split != "all" and row["split"] != split:
            continue
        match = classify(row["text"])
        entry = stats[row["set"]]
        entry["n"] += 1
        if match is not None:
            entry["blocked"] += 1
            flagged[row["set"]].append((row["text"], match[1]))
            phrases[row["set"]][match[1]] += 1
        else:
            missed[row["set"]].append(row["text"])

    REPORTS.mkdir(parents=True, exist_ok=True)
    failures = 0
    print(f"\nsplit={split} engine={engine}   (95% Wilson interval in brackets)\n")
    for name, (expect, authoritative) in SETS.items():
        entry = stats.get(name)
        if not entry or not entry["n"]:
            continue
        n, blocked = entry["n"], entry["blocked"]
        rate = blocked / n
        lo, hi = wilson(blocked, n)
        if expect == "allow":
            ok_rate = 1 - rate
            lo, hi = 1 - hi, 1 - lo
            label = f"allowed correctly {ok_rate:6.1%} [{lo:.1%}-{hi:.1%}]  (false-positive {rate:.1%})"
        elif expect == "block":
            label = f"blocked         {rate:6.1%} [{lo:.1%}-{hi:.1%}]"
        else:
            label = f"block rate      {rate:6.1%} [{lo:.1%}-{hi:.1%}]  (informational, read the samples)"
        tag = "AUTH" if authoritative else "info"
        print(f"[{tag}] {name:20} n={n:5}  {label}")
        (REPORTS / f"{name}.{split}.missed.txt").write_text("\n".join(missed[name]), encoding="utf-8")
        (REPORTS / f"{name}.{split}.flagged.txt").write_text(
            "\n".join(f"{why}\t{text}" for text, why in flagged[name]), encoding="utf-8"
        )

    if show:
        for name, (expect, _) in SETS.items():
            if name not in stats:
                continue
            if expect == "allow" or expect == "review":
                print(f"\n--- {name}: top triggering phrases ---")
                for why, count in phrases[name].most_common(8):
                    print(f"   {count:4}  {why}")
                for text, why in flagged[name][:show]:
                    print(f"   flagged [{why}] {text[:70]}")
            elif expect == "block":
                print(f"\n--- {name}: sample misses ---")
                for text in missed[name][:show]:
                    print(f"   {text[:80]}")
    accuracy_summary(stats)
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("fetch", "build", "run"))
    parser.add_argument("--split", choices=("dev", "test", "all"), default="dev")
    parser.add_argument("--show", type=int, default=0, help="print N sample rows per set")
    parser.add_argument("--engine", choices=("rules", "model", "combined"), default="rules")
    parser.add_argument("--challenge", action="store_true", help="score the hand-written independent set")
    parser.add_argument("--holdout", action="store_true", help="first holdout set (its misses were seen: now a dev set)")
    parser.add_argument("--holdout2", action="store_true", help="score the final, never-tuned-on hand-written set")
    parser.add_argument("--synth", action="store_true", help="score template families held out from training")
    args = parser.parse_args()
    if args.command == "fetch":
        fetch()
        return 0
    if args.command == "build":
        build()
        return 0
    return run(args.split, args.show, args.engine, args.challenge, args.synth, args.holdout, args.holdout2)


if __name__ == "__main__":
    sys.exit(main())
