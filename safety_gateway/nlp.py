"""Chinese NLP for Presidio: zh_core_web_md when installed, otherwise a no-op engine."""

from __future__ import annotations

from threading import Lock

from presidio_analyzer.nlp_engine import NoOpNlpEngine, NlpEngine, NlpEngineProvider

ZH_SPACY_MODEL = "zh_core_web_md"

# DATE/GPE/ORG from this model over-redact homework (今天、3月、12加35) and
# steal school/address spans. PERSON is the useful Traditional Chinese gain.
NLP_CONFIGURATION: dict[str, object] = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "zh", "model_name": ZH_SPACY_MODEL}],
    "ner_model_configuration": {
        "labels_to_ignore": [
            "DATE",
            "TIME",
            "CARDINAL",
            "EVENT",
            "QUANTITY",
            "ORDINAL",
            "PERCENT",
            "MONEY",
            "LANGUAGE",
            "LAW",
            "WORK_OF_ART",
            "PRODUCT",
            "FAC",
            "GPE",
            "LOC",
            "ORG",
            "NORP",
        ],
        "model_to_presidio_entity_mapping": {"PERSON": "PERSON", "PER": "PERSON"},
    },
}

_ENGINE: NlpEngine | None = None
_ENGINE_LOCK = Lock()


class BlankNlpEngine(NoOpNlpEngine):
    """Presidio no-op engine preconfigured for Traditional Chinese analysis."""

    def __init__(self) -> None:
        super().__init__(models=[{"lang_code": "zh", "model_name": "noop"}])


def spacy_zh_available(model_name: str = ZH_SPACY_MODEL) -> bool:
    try:
        import spacy
    except ImportError:
        return False
    return bool(spacy.util.is_package(model_name))


def create_nlp_engine() -> NlpEngine:
    """Load spaCy zh when the model is present; otherwise keep regex-only analysis."""
    if not spacy_zh_available():
        return BlankNlpEngine()
    provider = NlpEngineProvider(nlp_configuration=NLP_CONFIGURATION)
    return provider.create_engine()


def get_nlp_engine() -> NlpEngine:
    """Process-wide engine so tests and the playground do not reload 74MB each call."""
    global _ENGINE
    with _ENGINE_LOCK:
        if _ENGINE is None:
            _ENGINE = create_nlp_engine()
        return _ENGINE
