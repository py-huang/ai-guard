"""Quality gate for the locally trained classifier.

The artifact lives in the git-ignored `.cache/` (it is trained on public datasets that are not
committed), so these tests skip on a fresh clone and on CI. They run wherever the model exists and
catch a retrain, a rule edit or a threshold change that makes the gateway worse.

Only the development challenge set is gated here. The final holdout set is deliberately left out:
a test that fails on it invites tuning on it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from safety_gateway.steps.content_model import load_if_present
from safety_gateway.steps.content_safety import ContentSafetyStep

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / ".cache" / "models" / "content_safety"
CHALLENGE = ROOT / "tests" / "fixtures" / "content_safety_challenge.jsonl"

pytestmark = pytest.mark.skipif(
    not (MODEL_DIR / "meta.json").exists(), reason="no locally trained model (run scripts/train_content_model.py)"
)


def _rows() -> list[dict[str, str]]:
    return [json.loads(line) for line in CHALLENGE.read_text(encoding="utf-8").split("\n") if line]


@pytest.fixture(scope="module")
def step() -> ContentSafetyStep:
    model = load_if_present(MODEL_DIR)
    assert model is not None
    return ContentSafetyStep(model=model)


def test_the_model_clears_the_accuracy_bar_on_hand_written_sentences(step: ContentSafetyStep) -> None:
    rows = _rows()
    hits = sum((step.classify(r["text"]) is not None) == (r["expect"] == "block") for r in rows)
    assert hits / len(rows) >= 0.90


def test_the_model_does_not_make_children_ordinary_requests_look_dangerous(step: ContentSafetyStep) -> None:
    allow = [r["text"] for r in _rows() if r["expect"] == "allow"]
    blocked = [t for t in allow if step.classify(t) is not None]
    assert len(blocked) / len(allow) <= 0.10, blocked


def test_the_model_beats_the_rules_alone_on_harmful_recall(step: ContentSafetyStep) -> None:
    rules = ContentSafetyStep()
    harmful = [r["text"] for r in _rows() if r["expect"] == "block"]
    with_model = sum(step.classify(t) is not None for t in harmful)
    without = sum(rules.classify(t) is not None for t in harmful)
    assert with_model >= without + 10
