"""Session vault abstractions. In-memory today, Redis-shaped for drop-in replacement."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseSessionVault(ABC):
    """Maps original PII values to deterministic placeholders for one `session_id`.

    A Redis implementation should keep the same key layout:

    * `session:{id}:values`  -> HASH of `{entity_type}\\x1f{original}` -> token
    * `session:{id}:tokens`  -> HASH of token -> original
    * `session:{id}:counters` -> HASH of entity_type -> last issued index

    Sensitive originals must never be written to disk by this process.
    """

    @abstractmethod
    def get_or_create_token(self, session_id: str, entity_type: str, original: str) -> str:
        """Return a stable `<TYPE_N>` token for this value within the session."""

    @abstractmethod
    def resolve_token(self, session_id: str, token: str) -> str | None:
        """Look up the original value for a previously issued token."""

    @abstractmethod
    def deanonymize_text(self, session_id: str, text: str) -> str:
        """Replace issued placeholders in `text` with their original values."""

    @abstractmethod
    def list_mappings(self, session_id: str) -> dict[str, str]:
        """Return token -> original for the session (empty dict if unknown)."""

    @abstractmethod
    def clear_session(self, session_id: str) -> None:
        """Drop all mappings for a session (e.g. child logout / TTL expiry)."""
