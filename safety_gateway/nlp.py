"""NLP engine for regex-only Taiwan recognizers (no spaCy NER model required)."""

from __future__ import annotations

from presidio_analyzer.nlp_engine import NoOpNlpEngine


class BlankNlpEngine(NoOpNlpEngine):
    """Presidio no-op engine preconfigured for Traditional Chinese analysis."""

    def __init__(self) -> None:
        super().__init__(models=[{"lang_code": "zh", "model_name": "noop"}])
