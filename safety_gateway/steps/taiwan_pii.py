"""Inbound tokenization and outbound deanonymization for Taiwan PII."""

from __future__ import annotations

from typing import ClassVar

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine

from safety_gateway.pii.analyzer import build_analyzer_engine
from safety_gateway.pii.tokenizer import anonymize_with_vault, select_non_overlapping
from safety_gateway.schemas import DetectedEntity
from safety_gateway.steps.base import BaseGuardStep, GuardContext
from safety_gateway.vault.base import BaseSessionVault


class TaiwanPIIGuardStep(BaseGuardStep):
    name: ClassVar[str] = "taiwan_pii"

    def __init__(
        self,
        vault: BaseSessionVault,
        analyzer: AnalyzerEngine | None = None,
        anonymizer: AnonymizerEngine | None = None,
        language: str = "zh",
        score_threshold: float = 0.4,
    ) -> None:
        self._vault = vault
        self._analyzer = analyzer or build_analyzer_engine()
        self._anonymizer = anonymizer or AnonymizerEngine()
        self._language = language
        self._score_threshold = score_threshold

    @property
    def analyzer(self) -> AnalyzerEngine:
        return self._analyzer

    def process_inbound(self, context: GuardContext) -> GuardContext:
        analyzer_results = self._analyzer.analyze(
            text=context.text,
            language=self._language,
            score_threshold=self._score_threshold,
        )
        selected = select_non_overlapping(analyzer_results)
        tokenized = anonymize_with_vault(
            text=context.text,
            session_id=context.session_id,
            results=selected,
            vault=self._vault,
            anonymizer=self._anonymizer,
        )
        context.entities.extend(self._to_entities(context.text, context.session_id, selected))
        context.text = tokenized
        context.mark_step(self.name)
        return context

    def process_outbound(self, context: GuardContext) -> GuardContext:
        context.text = self.deanonymize_text(context.session_id, context.text)
        context.mark_step(self.name)
        return context

    def deanonymize_text(self, session_id: str, text: str) -> str:
        return self._vault.deanonymize_text(session_id, text)

    def _to_entities(
        self,
        original_text: str,
        session_id: str,
        results: list[RecognizerResult],
    ) -> list[DetectedEntity]:
        entities: list[DetectedEntity] = []
        for result in results:
            original = original_text[result.start : result.end]
            token = self._vault.get_or_create_token(session_id, result.entity_type, original)
            entities.append(
                DetectedEntity(
                    entity_type=result.entity_type,
                    original=original,
                    token=token,
                    start=result.start,
                    end=result.end,
                    score=float(result.score),
                )
            )
        return entities
