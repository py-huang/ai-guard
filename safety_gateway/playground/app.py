"""Local playground HTTP app: child chat + stakeholder prototype tabs."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.playground.features import FEATURES
from safety_gateway.playground.llm import resolve_backend
from safety_gateway.playground.service import PlaygroundChat
from safety_gateway.schemas import StrictModel
from safety_gateway.vault.memory import InMemorySessionVault

STATIC_DIR = Path(__file__).resolve().parent / "static"


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
        }

    @app.get("/api/features")
    def features() -> dict[str, object]:
        return {"features": FEATURES}

    @app.get("/api/evidence")
    def evidence(session_id: str = Query(min_length=1, max_length=128)) -> dict[str, object]:
        turns = playground.evidence(session_id)
        return {
            "session_id": session_id,
            "turns": [turn.model_dump() for turn in turns],
            "protected_entity_count": sum(len(turn.entities) for turn in turns),
            "leak_count": sum(1 for turn in turns if turn.pii_leaked_to_llm),
        }

    @app.post("/api/chat")
    def chat(request: ChatRequest) -> dict[str, object]:
        key = _env_gemini_key() or request.gemini_api_key
        llm = resolve_backend(key)
        try:
            result = playground.chat(request.session_id, request.text, llm)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"LLM 呼叫失敗：{exc}") from exc
        return result.model_dump()

    @app.post("/api/reset")
    def reset(request: ResetRequest) -> dict[str, bool]:
        playground.reset(request.session_id)
        return {"ok": True}

    @app.get("/")
    def index() -> FileResponse:
        return FileResponse(
            STATIC_DIR / "index.html",
            headers={"Cache-Control": "no-store"},
        )

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
    return app


app = create_app()
