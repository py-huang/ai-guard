"""Analyzer factory: zh spaCy NER (PERSON) + Presidio pattern defaults + Taiwan counterparts."""

from __future__ import annotations

import re

from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerRegistry, RecognizerResult
from presidio_analyzer.context_aware_enhancers import ContextAwareEnhancer
from presidio_analyzer.nlp_engine import NoOpNlpEngine
from presidio_analyzer.predefined_recognizers import SpacyRecognizer

from safety_gateway.nlp import get_nlp_engine
from safety_gateway.pii.presidio_defaults import build_predefined_recognizers_for_zh
from safety_gateway.pii.recognizers import build_taiwan_recognizers

_ID_LIKE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-_/]{4,}$")
_CJK_CHAR = re.compile(r"[\u4e00-\u9fa5]")
_LATIN_CHAR = re.compile(r"[A-Za-z]")


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


class TaiwanSpacyRecognizer(SpacyRecognizer):
    """zh_core_web_md PERSON only; drop passport/ID-shaped spans the model mislabels."""

    def analyze(  # type: ignore[no-untyped-def]
        self,
        text,
        entities,
        nlp_artifacts=None,
    ) -> list[RecognizerResult]:
        results = super().analyze(text, entities, nlp_artifacts)
        kept: list[RecognizerResult] = []
        for item in results:
            span = text[item.start : item.end]
            if not _keep_spacy_person(span):
                continue
            kept.append(item)
        return kept


def _keep_spacy_person(span: str) -> bool:
    """zh_core_web_md tags 電話 as PERSON; keep 3+ CJK names or Latin names."""
    if _ID_LIKE.fullmatch(span):
        return False
    if _LATIN_CHAR.search(span):
        return True
    return len(_CJK_CHAR.findall(span)) >= 3


def build_analyzer_engine(
    extra_recognizers: list[EntityRecognizer] | None = None,
) -> AnalyzerEngine:
    nlp_engine = get_nlp_engine()
    recognizers: list[EntityRecognizer] = []
    recognizers.extend(build_predefined_recognizers_for_zh())
    recognizers.extend(build_taiwan_recognizers())
    if not isinstance(nlp_engine, NoOpNlpEngine):
        recognizers.append(
            TaiwanSpacyRecognizer(
                supported_language="zh",
                supported_entities=["PERSON"],
                name="SpacyRecognizer_zh",
            )
        )
    if extra_recognizers:
        recognizers.extend(extra_recognizers)
    registry = RecognizerRegistry(recognizers=recognizers, supported_languages=["zh"])
    return AnalyzerEngine(
        registry=registry,
        nlp_engine=nlp_engine,
        supported_languages=["zh"],
        default_score_threshold=0.4,
        context_aware_enhancer=PassThroughContextEnhancer(),  # type: ignore[arg-type]
    )
