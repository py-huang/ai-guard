"""Local playground HTTP app: child chat + stakeholder prototype tabs."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.image import ImageOcrUnavailable
from safety_gateway.playground.features import FEATURES, TUNABLES
from safety_gateway.playground.llm import (
    LlmBusyError,
    LlmError,
    child_safe_llm_message,
    is_retryable_llm_error,
    resolve_backend,
)
from safety_gateway.playground.service import PlaygroundChat
from safety_gateway.schemas import StrictModel
from safety_gateway.vault.memory import InMemorySessionVault

STATIC_DIR = Path(__file__).resolve().parent / "static"
GENERATED_IMAGE = STATIC_DIR / "taiwan-contact-book-pii.png"
CLASSMATE_IMAGE = STATIC_DIR / "classmate-nametag-portrait.png"


class ChatRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=4000)
    gemini_api_key: str | None = Field(default=None, max_length=256)


class ResetRequest(StrictModel):
    session_id: str = Field(min_length=1, max_length=128)


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


def create_app() -> FastAPI:
    _load_dotenv()
    gateway = AISafetyGateway(vault=InMemorySessionVault())
    playground = PlaygroundChat(gateway)
    app = FastAPI(title="AI Guard Prototype", docs_url=None, redoc_url=None)

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
        }

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

    @app.post("/api/chat")
    def chat(request: ChatRequest) -> dict[str, object]:
        key = _env_gemini_key() or request.gemini_api_key
        llm = resolve_backend(key)
        try:
            result = playground.chat(request.session_id, request.text, llm)
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
        session_id: str = Query(min_length=1, max_length=128),
        file: UploadFile = File(...),
    ) -> Response:
        raw = file.file.read()
        if not raw:
            raise _http_error(400, "請先選擇一張照片。", False)
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

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "index.html",
            headers={"Cache-Control": "no-store"},
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
