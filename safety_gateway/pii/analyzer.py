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
from safety_gateway.pii.taiwan_names import is_everyday_word, is_plausible_tw_name

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
            if not _keep_spacy_person(span) or is_everyday_word(text, item.start, item.end):
                continue
            kept.append(item)
        return kept


_NAME_JOINERS = "·・‧•"
# Latin: one to four capitalised words ("Gary", "Henry Link"). Anything with digits, symbols or
# lower-case-only tokens is code, a URL, a filename or an ordinary word.
_LATIN_NAME = re.compile(r"[A-Z][a-z]{1,15}(?:[ \-'][A-Z][a-z]{1,15}){0,3}")
_LATIN_NOT_NAMES = frozenset({"The", "This", "That", "These", "Those", "There", "What", "When", "Where", "Which"})
# Particles, pronouns and function words never sit inside a Chinese given name; a "name" that
# contains one is a clause fragment the NER model over-extended ("分類以下為", "將書籍").
_FUNCTION_CHARS = frozenset("的了是在不有與為嗎呢吧還別個請這那以下將把被從對於或及就都也很更最並但而")


def _keep_spacy_person(span: str) -> bool:
    """Keep what looks like a person's name; drop IDs, code, group nouns and clause fragments.

    spaCy's zh PERSON label is noisy on ordinary text (nationalities, places, code, noun phrases),
    and every false positive is a word the child never sees again. The rules here trade a small
    amount of recall on unusual names for far fewer over-masked sentences; the targeted pattern
    recognizers (我叫…, 同學…) still catch names that are introduced as names.
    """
    if _ID_LIKE.fullmatch(span):
        return False
    has_latin = bool(_LATIN_CHAR.search(span))
    cjk = len(_CJK_CHAR.findall(span))
    if has_latin and cjk:
        return False  # "Java程式", "sp山風", "Nike鞋": a mixed token is a term, not a name
    if has_latin:
        words = span.split()
        return bool(_LATIN_NAME.fullmatch(span)) and words[0] not in _LATIN_NOT_NAMES
    if any(joiner in span for joiner in _NAME_JOINERS):
        # Transliterated foreign name ("約翰·格林"): parts are long and arbitrary.
        return cjk >= 3 and not any(char in _FUNCTION_CHARS for char in span)
    if cjk < 2 or cjk > 4 or any(char in _FUNCTION_CHARS for char in span) or span.endswith("人"):
        return False  # group nouns ("中國人", "一個人") and long clause fragments
    return is_plausible_tw_name(span)


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
        default_score_threshold=0.1,
        context_aware_enhancer=PassThroughContextEnhancer(),  # type: ignore[arg-type]
    )
