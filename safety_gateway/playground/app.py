"""Local playground HTTP app: child chat + stakeholder prototype tabs."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.image import ImageOcrUnavailable
from safety_gateway.playground.access import (
    MAX_UPLOAD_BYTES,
    ChatRateLimiter,
    SecurityHeadersMiddleware,
    SharePasswordMiddleware,
    share_mode_enabled,
)
from safety_gateway.playground.features import FEATURES, TUNABLES
from safety_gateway.playground.llm import (
    LlmBusyError,
    LlmError,
    child_safe_llm_message,
    is_retryable_llm_error,
    resolve_backend,
)
from safety_gateway.playground.service import PlaygroundChat
from safety_gateway.playground.zhuyin import to_zhuyin_parts
from safety_gateway.schemas import StrictModel
from safety_gateway.vault.memory import InMemorySessionVault

STATIC_DIR = Path(__file__).resolve().parent / "static"
GENERATED_IMAGE = STATIC_DIR / "taiwan-contact-book-pii.png"
CLASSMATE_IMAGE = STATIC_DIR / "classmate-nametag-portrait.png"


class ChatRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=4000)
    lab: bool = False


class ResetRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=128)


class InspectRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=4000)


def _env_gemini_key() -> str | None:
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_GENAI_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return None


def _load_dotenv() -> None:
    env_path = Path.cwd() / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        cleaned = value.strip().strip("'").strip('"')
        if cleaned:
            os.environ[key.strip()] = cleaned


def _http_error(status: int, message: str, retryable: bool) -> HTTPException:
    return HTTPException(status_code=status, detail={"message": message, "retryable": retryable})


def _read_upload(request: Request, file: UploadFile) -> bytes:
    length = request.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_UPLOAD_BYTES + 64_000:
        raise _http_error(413, "照片太大，請用較小的檔案。", False)
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if not raw:
        raise _http_error(400, "請先選擇一張照片。", False)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise _http_error(413, "照片太大，請用較小的檔案。", False)
    return raw


def create_app() -> FastAPI:
    _load_dotenv()
    gateway = AISafetyGateway(vault=InMemorySessionVault())
    playground = PlaygroundChat(gateway)
    rate_limiter = ChatRateLimiter()
    app = FastAPI(title="AI Guard Prototype", docs_url=None, redoc_url=None)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(SharePasswordMiddleware)

    @app.get("/api/status")
    def status() -> dict[str, str | bool]:
        key = _env_gemini_key()
        backend = resolve_backend(key)
        return {
            "llm_backend": backend.name,
            "llm_model": backend.model,
            "env_key_configured": bool(key),
            "ocr_backend": "rapidocr",
            "ocr_scope": "venv",
            "share_password_required": share_mode_enabled(),
        }

    @app.get("/api/zhuyin")
    def zhuyin(text: str = Query(min_length=1, max_length=500)) -> dict[str, object]:
        return {"text": text, "parts": [part.model_dump() for part in to_zhuyin_parts(text)]}

    @app.get("/api/features")
    def features() -> dict[str, object]:
        return {"features": FEATURES, "tunables": TUNABLES}

    @app.get("/api/evidence")
    def evidence(session_id: str = Query(min_length=1, max_length=128)) -> dict[str, object]:
        turns = playground.evidence(session_id)
        return {
            "session_id": session_id,
            "turns": [turn.model_dump() for turn in turns],
            "protected_entity_count": sum(len(turn.entities) for turn in turns),
            "leak_count": sum(1 for turn in turns if turn.pii_leaked_to_llm),
        }

    @app.get("/api/audit")
    def audit(
        session_id: str = Query(min_length=1, max_length=128),
        restore: bool = False,
    ) -> dict[str, object]:
        events = []
        for event in gateway.audit_log.list_session(session_id):
            payload = event.model_dump()
            display = event.sanitized_text
            if restore and not event.blocked:
                display = gateway.deanonymize_text(session_id, event.sanitized_text)
            payload["display_text"] = display
            events.append(payload)
        return {"session_id": session_id, "restore": restore, "events": events}

    @app.post("/api/inspect")
    def inspect(request: InspectRequest) -> dict[str, object]:
        result = gateway.process_inbound(request.session_id, request.text)
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

    @app.post("/api/chat")
    def chat(request: ChatRequest) -> dict[str, object]:
        return _chat_turn(request.session_id, request.text, None, request.lab)

    @app.post("/api/chat-with-image")
    def chat_with_image(
        request: Request,
        session_id: str = Form(..., min_length=1, max_length=128),
        text: str = Form(..., min_length=1, max_length=4000),
        lab: bool = Form(False),
        file: UploadFile = File(...),
    ) -> dict[str, object]:
        if not lab:
            raise _http_error(400, "附照片請到測試頁再試。", False)
        raw = _read_upload(request, file)
        return _chat_turn(session_id, text, raw, True)

    def _chat_turn(
        session_id: str,
        text: str,
        image_bytes: bytes | None,
        lab: bool,
    ) -> dict[str, object]:
        if not rate_limiter.allow():
            raise _http_error(429, "現在太多人在問，請稍等再試。", True)
        llm = resolve_backend(_env_gemini_key())
        try:
            result = playground.chat(
                session_id,
                text,
                llm,
                image_bytes=image_bytes,
                enable_images=lab,
            )
        except LlmBusyError as exc:
            raise _http_error(503, exc.child_message, True) from exc
        except LlmError as exc:
            raise _http_error(502, exc.child_message, False) from exc
        except Exception as exc:
            raise _http_error(
                503 if is_retryable_llm_error(exc) else 502,
                child_safe_llm_message(exc),
                is_retryable_llm_error(exc),
            ) from exc
        return result.model_dump()

    @app.post("/api/reset")
    def reset(request: ResetRequest) -> dict[str, bool]:
        playground.reset(request.session_id)
        return {"ok": True}

    @app.get("/api/demo-image")
    def demo_image(redacted: bool = False) -> Response:
        original, redacted_png = gateway.demo_contact_book()
        return Response(
            content=redacted_png if redacted else original,
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/api/generated-image")
    def generated_image() -> FileResponse:
        if not GENERATED_IMAGE.is_file():
            raise _http_error(404, "還沒有生成的示範照片。", False)
        return FileResponse(GENERATED_IMAGE, media_type="image/png")

    @app.get("/api/classmate-image")
    def classmate_image() -> FileResponse:
        if not CLASSMATE_IMAGE.is_file():
            raise _http_error(404, "還沒有同學名牌示範照片。", False)
        return FileResponse(CLASSMATE_IMAGE, media_type="image/png")

    @app.post("/api/redact-classmate-image")
    def redact_classmate_image(
        session_id: str = Query(min_length=1, max_length=128),
    ) -> Response:
        if not CLASSMATE_IMAGE.is_file():
            raise _http_error(404, "還沒有同學名牌示範照片。", False)
        try:
            result = gateway.redact_image(session_id, CLASSMATE_IMAGE.read_bytes())
        except ImageOcrUnavailable as exc:
            raise _http_error(503, str(exc), False) from exc
        return Response(
            content=result.image_bytes,
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/api/redact-generated-image")
    def redact_generated_image(
        session_id: str = Query(min_length=1, max_length=128),
    ) -> Response:
        if not GENERATED_IMAGE.is_file():
            raise _http_error(404, "還沒有生成的示範照片。", False)
        try:
            result = gateway.redact_image(session_id, GENERATED_IMAGE.read_bytes())
        except ImageOcrUnavailable as exc:
            raise _http_error(503, str(exc), False) from exc
        return Response(
            content=result.image_bytes,
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )

    @app.post("/api/redact-image")
    def redact_image(
        request: Request,
        session_id: str = Query(min_length=1, max_length=128),
        file: UploadFile = File(...),
    ) -> Response:
        raw = _read_upload(request, file)
        try:
            result = gateway.redact_image(session_id, raw)
        except ImageOcrUnavailable as exc:
            raise _http_error(503, str(exc), False) from exc
        except Exception:
            raise _http_error(400, "這張照片現在沒辦法遮碼，請改用示範聯絡簿。", False)
        return Response(
            content=result.image_bytes,
            media_type="image/png",
            headers={"Cache-Control": "no-store"},
        )

    def _html(name: str) -> FileResponse:
        return FileResponse(
            STATIC_DIR / name,
            headers={"Cache-Control": "no-store"},
        )

    @app.get("/")
    def index() -> FileResponse:
        return _html("index.html")

    @app.get("/intro")
    def intro() -> FileResponse:
        return _html("intro.html")

    @app.get("/chat")
    def chat_alias() -> RedirectResponse:
        return RedirectResponse(url="/", status_code=307)

    @app.get("/zhuyin")
    def zhuyin_lab() -> FileResponse:
        return _html("zhuyin.html")

    @app.get("/test")
    def test_index() -> FileResponse:
        return _html("index.html")

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
