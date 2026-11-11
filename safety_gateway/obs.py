"""Structured, PII-free logging.

Rule: log *facts about* a request (route, status, duration, ids, counts), never the
child's text, never the originals held in the vault, never image bytes.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

LOGGER_NAME = "safety_gateway"

# Keys callers may attach via ``extra=``. Anything else is dropped on purpose so a
# careless ``extra={"text": ...}`` cannot leak into the log stream.
_ALLOWED_FIELDS = (
    "request_id",
    "method",
    "path",
    "status",
    "duration_ms",
    "event",
    "reason",
    "exc_type",
    "entities",
    "blocked",
    "sessions",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "msg": record.getMessage(),
        }
        for key in _ALLOWED_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def configure_logging(level: str = "INFO") -> None:
    """Idempotent: installs one JSON stream handler on the package logger."""
    logger = get_logger()
    if any(getattr(handler, "_safety_gateway", False) for handler in logger.handlers):
        logger.setLevel(level.upper())
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._safety_gateway = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False
