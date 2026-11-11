"""Production Safety Gateway HTTP service.

This is the only process the Next.js BFF talks to. It exposes the guard pipeline and
nothing else: no chat, no demo images, no evidence or restore endpoints. The
experimental UI lives in ``safety_gateway.playground`` and is a separate app.

Run:  python -m safety_gateway.server --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from PIL import Image, UnidentifiedImageError
from pydantic import Field

from safety_gateway.audit.memory import InMemoryAuditLog
from safety_gateway.gateway import AISafetyGateway
from safety_gateway.obs import configure_logging, get_logger
from safety_gateway.pii.image import ImageOcrUnavailable
from safety_gateway.schemas import ImageRedactResult, SafetyProcessResult, StrictModel
from safety_gateway.server.security import (
    BodyLimitMiddleware,
    GatewayGuardMiddleware,
    SlidingWindowLimiter,
    error_response,
)
from safety_gateway.server.settings import GatewaySettings, SettingsError
from safety_gateway.steps.content_model import ContentModel, load_if_present
from safety_gateway.vault.memory import InMemorySessionVault

# Session ids are echoed into logs and used as dict keys: keep them boring.
SESSION_ID_PATTERN = r"^[A-Za-z0-9_.:\-]{1,128}$"

# A 5 MB PNG can still decompress to gigapixels. Refuse before PIL allocates it.
MAX_IMAGE_PIXELS = 40_000_000

_logger = get_logger()


class GatewayBusy(Exception):
    """No analysis slot became free in time; the caller should retry shortly."""


class SessionRequest(StrictModel):
    session_id: str = Field(pattern=SESSION_ID_PATTERN)


class TextRequest(SessionRequest):
    text: str = Field(min_length=1)


def _inspect_payload(result: SafetyProcessResult) -> dict[str, object]:
    """Wire format shared with the Next.js client (`lib/gateway.ts`). Do not rename keys."""
    return {
        "session_id": result.session_id,
        "blocked": result.blocked,
        "block_category": result.block_category,
        "child_message": result.child_message,
        "processed_text": result.processed_text,
        "entities": [
            {
                "entity_type": entity.entity_type,
                "original": entity.original,
                "token": entity.token,
            }
            for entity in result.entities
        ],
    }


def _png_response(result: ImageRedactResult) -> Response:
    return Response(
        content=result.image_bytes,
        media_type="image/png",
        headers={
            "Cache-Control": "no-store",
            "X-Detected-Entities": ",".join(result.detected_entities),
            "X-Redact-Coverage": f"{result.coverage:.4f}",
            "X-Image-Blocked": "1" if result.blocked else "0",
            "X-Block-Reason": result.block_reason or "",
        },
    )


def build_gateway(settings: GatewaySettings) -> AISafetyGateway:
    """Wire the guard chain with bounded, TTL-limited stores."""
    vault = InMemorySessionVault(
        ttl_seconds=settings.vault_ttl_seconds,
        max_sessions=settings.vault_max_sessions,
    )
    audit = InMemoryAuditLog(
        max_events=settings.audit_max_events_per_session,
        max_sessions=settings.audit_max_sessions,
    )
    return AISafetyGateway(
        vault=vault, audit_log=audit, content_model=load_content_model(settings)
    )


def load_content_model(settings: GatewaySettings) -> ContentModel | None:
    """The trained classifier, or ``None`` (rules only) when none was configured or trained."""
    model = load_if_present(settings.content_model_dir)
    if model is None and settings.content_model_required:
        raise SettingsError(
            f"GATEWAY_CONTENT_MODEL_DIR={settings.content_model_dir!r} has no trained model; "
            "run scripts/train_content_model.py or unset it"
        )
    if model is None:
        _logger.info("content model: none, running on phrase rules", extra={"event": "content_model"})
    else:
        _logger.info(
            "content model loaded",
            extra={"event": "content_model", "threshold": model.threshold},
        )
    return model


def create_app(
    settings: GatewaySettings | None = None,
    gateway: AISafetyGateway | None = None,
) -> FastAPI:
    settings = settings or GatewaySettings.from_env()
    configure_logging()
    Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS
    guard = gateway or build_gateway(settings)

    inspect_limiter = SlidingWindowLimiter(settings.inspect_per_minute)
    image_limiter = SlidingWindowLimiter(settings.image_per_minute)
    image_slots = threading.BoundedSemaphore(settings.max_concurrent_images)
    analysis_slots = threading.BoundedSemaphore(settings.max_concurrent_analysis)

    @contextmanager
    def analysis_slot() -> Iterator[None]:
        if not analysis_slots.acquire(timeout=settings.analysis_queue_seconds):
            raise GatewayBusy
        try:
            yield
        finally:
            analysis_slots.release()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.warmup:
            # Load Presidio + spaCy before we claim readiness, so the first child
            # request never pays model-load latency (or times out because of it).
            guard.sanitize_text("__warmup__", "我叫王小明，電話0912345678。")
            guard.reset_session("__warmup__")
        app.state.ready = True
        if not settings.auth_enabled:
            _logger.warning(
                "SAFETY_GATEWAY_TOKEN is not set: gateway accepts anonymous callers",
                extra={"event": "auth_disabled"},
            )
        _logger.info("gateway ready", extra={"event": "ready"})
        try:
            yield
        finally:
            # Originals of children's PII must not outlive the process.
            guard.vault.clear_all()
            guard.audit_log.clear_all()
            _logger.info("gateway stopped", extra={"event": "stopped"})

    app = FastAPI(
        title="AI Guard Safety Gateway",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.ready = not settings.warmup
    app.state.settings = settings
    app.state.gateway = guard
    # Added first = innermost: the guard authenticates and logs, then the limiter caps bytes.
    app.add_middleware(BodyLimitMiddleware, settings=settings)
    app.add_middleware(GatewayGuardMiddleware, settings=settings)

    @app.exception_handler(GatewayBusy)
    async def busy(request: Request, exc: GatewayBusy) -> JSONResponse:
        return error_response(503, "busy", retryable=True)

    @app.exception_handler(Exception)
    async def unhandled(request: Request, exc: Exception) -> JSONResponse:
        _logger.error(
            "unhandled error",
            extra={
                "event": "unhandled",
                "request_id": getattr(request.state, "request_id", None),
                "path": request.url.path,
                "exc_type": type(exc).__name__,
            },
        )
        return error_response(500, "internal error")

    # --- probes ---------------------------------------------------------------------

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> Response:
        if not app.state.ready:
            return error_response(503, "warming up", retryable=True)
        return JSONResponse(
            {
                "status": "ready",
                "auth": settings.auth_enabled,
                "content_model": bool(getattr(guard.safety_step, "has_model", False)),
            }
        )

    # --- guard pipeline -------------------------------------------------------------

    @app.post("/api/inspect")
    def inspect(request: TextRequest) -> Response:
        """Full inbound pipeline for a new child message (PII, safety, Socratic, audit)."""
        if len(request.text) > settings.max_inspect_chars:
            return error_response(422, "text too long")
        if not inspect_limiter.allow():
            return error_response(429, "too many requests", retryable=True)
        with analysis_slot():
            result = guard.process_inbound(request.session_id, request.text)
        _log_result("inspect", result)
        return JSONResponse(_inspect_payload(result), headers={"Cache-Control": "no-store"})

    @app.post("/api/sanitize")
    def sanitize(request: TextRequest) -> Response:
        """Idempotent re-check of text the BFF is about to send to (or got from) an LLM.

        No Socratic prefix and no audit event, so it can run on history and on model
        output every turn without side effects beyond vault tokens.
        """
        if len(request.text) > settings.max_sanitize_chars:
            return error_response(422, "text too long")
        if not inspect_limiter.allow():
            return error_response(429, "too many requests", retryable=True)
        with analysis_slot():
            result = guard.sanitize_text(request.session_id, request.text)
        _log_result("sanitize", result)
        return JSONResponse(_inspect_payload(result), headers={"Cache-Control": "no-store"})

    @app.post("/api/moderate-output")
    def moderate_output(request: TextRequest) -> Response:
        """Content-safety check on a model reply before a child can see it."""
        if len(request.text) > settings.max_sanitize_chars:
            return error_response(422, "text too long")
        if not inspect_limiter.allow():
            return error_response(429, "too many requests", retryable=True)
        with analysis_slot():
            result = guard.moderate_output(request.session_id, request.text)
        _log_result("moderate_output", result)
        return JSONResponse(_inspect_payload(result), headers={"Cache-Control": "no-store"})

    @app.post("/api/redact-image")
    def redact_image(
        request: Request,
        session_id: str = Query(pattern=SESSION_ID_PATTERN),
        file: UploadFile = File(...),
    ) -> Response:
        if not image_limiter.allow():
            return error_response(429, "too many requests", retryable=True)
        raw = file.file.read(settings.max_upload_bytes + 1)
        if not raw:
            return error_response(400, "empty upload")
        if len(raw) > settings.max_upload_bytes:
            return error_response(413, "payload too large")
        if not image_slots.acquire(blocking=False):
            # OCR is CPU-bound; shed load instead of queueing until everything times out.
            return error_response(503, "busy", retryable=True)
        try:
            result = guard.redact_image(session_id, raw)
        except ImageOcrUnavailable:
            return error_response(503, "ocr unavailable")
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, ValueError):
            return error_response(400, "unreadable image")
        finally:
            image_slots.release()
        _logger.info(
            "image checked",
            extra={
                "event": "redact_image",
                "request_id": getattr(request.state, "request_id", None),
                "blocked": result.blocked,
                "reason": result.block_reason,
                "entities": len(result.detected_entities),
            },
        )
        return _png_response(result)

    @app.post("/api/session/reset")
    def reset_session(request: SessionRequest) -> dict[str, bool]:
        """Forget one session's vault mappings and audit trail (child logout / delete chat)."""
        guard.reset_session(request.session_id)
        return {"ok": True}

    return app


def _log_result(kind: str, result: SafetyProcessResult) -> None:
    _logger.info(
        kind,
        extra={
            "event": kind,
            "blocked": result.blocked,
            "reason": result.block_category,
            "entities": len(result.entities),
        },
    )
