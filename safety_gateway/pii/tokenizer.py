"""Convert analyzer hits into anonymizer recognizer results if the packages diverge."""

from __future__ import annotations

from collections.abc import Sequence

from presidio_analyzer import RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig
from presidio_anonymizer.entities import RecognizerResult as AnonymizerRecognizerResult

from safety_gateway.vault.base import BaseSessionVault


def select_non_overlapping(results: Sequence[RecognizerResult]) -> list[RecognizerResult]:
    """Keep highest-score, then longest, then leftmost spans; drop overlaps."""
    ranked = sorted(results, key=lambda item: (-item.score, -(item.end - item.start), item.start))
    chosen: list[RecognizerResult] = []
    for candidate in ranked:
        if any(_overlaps(candidate, kept) for kept in chosen):
            continue
        chosen.append(candidate)
    return sorted(chosen, key=lambda item: item.start)


def _overlaps(left: RecognizerResult, right: RecognizerResult) -> bool:
    return not (left.end <= right.start or left.start >= right.end)


def anonymize_with_vault(
    text: str,
    session_id: str,
    results: Sequence[RecognizerResult],
    vault: BaseSessionVault,
    anonymizer: AnonymizerEngine,
) -> str:
    """Replace detected spans with deterministic `<TYPE_N>` tokens stored in the vault."""
    if not results:
        return text

    def make_operator(entity_type: str) -> OperatorConfig:
        def _replace(original: str, bound_type: str = entity_type) -> str:
            return vault.get_or_create_token(session_id, bound_type, original)

        return OperatorConfig("custom", {"lambda": _replace})

    operators = {
        result.entity_type: make_operator(result.entity_type) for result in results
    }
    anonymizer_results = [
        AnonymizerRecognizerResult(
            entity_type=result.entity_type,
            start=result.start,
            end=result.end,
            score=result.score,
        )
        for result in results
    ]
    engine_result = anonymizer.anonymize(
        text=text,
        analyzer_results=anonymizer_results,
        operators=operators,
    )
    return engine_result.text
