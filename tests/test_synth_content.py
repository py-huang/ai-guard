from __future__ import annotations

from collections import Counter

from tests.synth_content import ACTS, UNSAFE_FRAMES, family_part, generate


def test_generation_is_deterministic() -> None:
    assert generate(seed=1) == generate(seed=1)
    assert generate(seed=1) != generate(seed=2)


def test_every_label_is_present_and_allow_is_not_a_minority() -> None:
    labels = Counter(sample.label for sample in generate())
    assert set(labels) == {"allow", "unsafe", "toxic", "injection"}
    assert labels["allow"] >= labels["unsafe"]


def test_family_split_never_mixes_a_template_across_parts() -> None:
    parts: dict[str, set[str]] = {}
    for sample in generate():
        parts.setdefault(sample.family, set()).add(family_part(sample.family))
    assert all(len(p) == 1 for p in parts.values())
    seen = {family_part(f) for f in parts}
    assert seen == {"train", "val", "test"}


def test_harmful_acts_also_appear_in_protective_sentences() -> None:
    """The point of the set: identical topic words on both sides of the label."""
    samples = generate()
    act = ACTS["theft"][0]
    texts = [s for s in samples if act in s.text]
    assert {s.label for s in texts} == {"unsafe", "allow"}


def test_unsafe_frames_are_filled_in() -> None:
    assert all("{act}" in frame for frame in UNSAFE_FRAMES)
    assert not any("{" in sample.text for sample in generate())
