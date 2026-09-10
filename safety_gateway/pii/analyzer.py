"""Presidio AnalyzerEngine factory registered with Taiwan custom recognizers only."""

from __future__ import annotations

from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerRegistry
from presidio_analyzer.context_aware_enhancers import ContextAwareEnhancer

from safety_gateway.nlp import BlankNlpEngine
from safety_gateway.pii.recognizers import build_taiwan_recognizers


class PassThroughContextEnhancer(ContextAwareEnhancer):
    """Skip lemma-window boosting; Chinese cues live inside the recognizers themselves."""

    def __init__(self) -> None:
        super().__init__(
            context_similarity_factor=0.0,
            min_score_with_context_similarity=0.0,
            context_prefix_count=0,
            context_suffix_count=0,
        )

    def enhance_using_context(self, text, raw_results, nlp_artifacts, recognizers, context=None):  # type: ignore[no-untyped-def]
        return raw_results


def build_analyzer_engine(
    extra_recognizers: list[EntityRecognizer] | None = None,
) -> AnalyzerEngine:
    recognizers = build_taiwan_recognizers()
    if extra_recognizers:
        recognizers.extend(extra_recognizers)
    registry = RecognizerRegistry(recognizers=recognizers, supported_languages=["zh"])
    return AnalyzerEngine(
        registry=registry,
        nlp_engine=BlankNlpEngine(),
        supported_languages=["zh"],
        default_score_threshold=0.4,
        context_aware_enhancer=PassThroughContextEnhancer(),  # type: ignore[arg-type]
    )
