"""Runtime settings for the production Safety Gateway service.

Everything is read from environment variables exactly once, in one place, so moving
from a laptop to a server only means changing the environment.
"""

from __future__ import annotations

import os
from pathlib import Path
from collections.abc import Mapping
from dataclasses import dataclass

_TRUE = {"1", "true", "yes", "on"}


_DEFAULT_MODEL_DIR = Path(__file__).resolve().parents[2] / ".cache" / "models" / "content_safety"


class SettingsError(RuntimeError):
    """Raised at startup when the environment is unsafe for the chosen mode."""


def _flag(env: Mapping[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    return raw.strip().lower() in _TRUE


def _number(env: Mapping[str, str], name: str, default: float, minimum: float) -> float:
    raw = env.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise SettingsError(f"{name} must be a number, got {raw!r}") from exc
    if value < minimum:
        raise SettingsError(f"{name} must be >= {minimum}, got {value}")
    return value


@dataclass(frozen=True)
class GatewaySettings:
    """Immutable, validated configuration for ``safety_gateway.server``."""

    environment: str = "development"
    token: str = ""

    # Request limits. The Next.js BFF enforces the same numbers before calling us.
    max_inspect_chars: int = 4_000
    max_sanitize_chars: int = 20_000
    max_upload_bytes: int = 5 * 1024 * 1024
    max_body_bytes: int = 128 * 1024

    # Abuse / capacity guards (global per process; the BFF is the only caller).
    inspect_per_minute: int = 600
    image_per_minute: int = 30
    max_concurrent_images: int = 2
    # CPU-bound NLP: more runnable threads than this only fight over the GIL (measured:
    # ~110 req/s at 4 concurrent vs ~16 req/s at 48). Excess requests queue instead.
    max_concurrent_analysis: int = 4
    analysis_queue_seconds: float = 6.0

    # PII vault + audit retention. Originals of a child's PII must not live forever.
    vault_ttl_seconds: float = 3_600.0
    vault_max_sessions: int = 5_000
    audit_max_events_per_session: int = 200
    audit_max_sessions: int = 1_000

    warmup: bool = True

    # Optional trained content classifier (see safety_gateway/steps/content_model.py).
    # Empty = rules only. If the directory was set explicitly it must exist: a gateway that
    # silently lost its model would be weaker than the operator believes.
    content_model_dir: str = ""
    content_model_required: bool = False

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def auth_enabled(self) -> bool:
        return bool(self.token)

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> GatewaySettings:
        source = os.environ if env is None else env
        environment = (source.get("GATEWAY_ENV") or "development").strip().lower()
        if environment not in {"development", "production", "test"}:
            raise SettingsError(
                f"GATEWAY_ENV must be development, production or test, got {environment!r}"
            )
        token = (source.get("SAFETY_GATEWAY_TOKEN") or "").strip()
        model_dir = (source.get("GATEWAY_CONTENT_MODEL_DIR") or "").strip()
        if model_dir.lower() in {"off", "none", "false", "0"}:
            model_dir, model_required = "", False
        elif model_dir:
            model_required = True
        else:
            # Local convenience only: use a model trained on this machine if there is one.
            model_required = False
            if environment == "development":
                model_dir = str(_DEFAULT_MODEL_DIR)
        upload = int(_number(source, "GATEWAY_MAX_UPLOAD_BYTES", 5 * 1024 * 1024, 1024))
        settings = cls(
            environment=environment,
            token=token,
            max_inspect_chars=int(_number(source, "GATEWAY_MAX_INSPECT_CHARS", 4_000, 1)),
            max_sanitize_chars=int(_number(source, "GATEWAY_MAX_SANITIZE_CHARS", 20_000, 1)),
            max_upload_bytes=upload,
            inspect_per_minute=int(_number(source, "GATEWAY_INSPECT_PER_MINUTE", 600, 1)),
            image_per_minute=int(_number(source, "GATEWAY_IMAGE_PER_MINUTE", 30, 1)),
            max_concurrent_images=int(_number(source, "GATEWAY_MAX_CONCURRENT_IMAGES", 2, 1)),
            max_concurrent_analysis=int(_number(source, "GATEWAY_MAX_CONCURRENT_ANALYSIS", 4, 1)),
            analysis_queue_seconds=_number(source, "GATEWAY_ANALYSIS_QUEUE_SECONDS", 6.0, 0.1),
            vault_ttl_seconds=_number(source, "GATEWAY_VAULT_TTL_SECONDS", 3_600.0, 1.0),
            vault_max_sessions=int(_number(source, "GATEWAY_VAULT_MAX_SESSIONS", 5_000, 1)),
            audit_max_events_per_session=int(
                _number(source, "GATEWAY_AUDIT_MAX_EVENTS", 200, 1)
            ),
            audit_max_sessions=int(_number(source, "GATEWAY_AUDIT_MAX_SESSIONS", 1_000, 1)),
            warmup=_flag(source, "GATEWAY_WARMUP", True),
            content_model_dir=model_dir,
            content_model_required=model_required,
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.is_production and not self.token:
            raise SettingsError(
                "SAFETY_GATEWAY_TOKEN is required when GATEWAY_ENV=production; "
                "the gateway returns children's data and must not be callable anonymously."
            )
        if self.token and len(self.token) < 16:
            raise SettingsError("SAFETY_GATEWAY_TOKEN must be at least 16 characters")
