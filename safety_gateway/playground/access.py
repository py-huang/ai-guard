"""Share-mode guards: password, rate limit, ignore client-supplied API keys."""

from __future__ import annotations

import base64
import os
import secrets
import time
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

SHARE_USERNAME = "demo"
MAX_UPLOAD_BYTES = 3 * 1024 * 1024
_CHAT_RATE = 40
_CHAT_WINDOW_SECONDS = 60.0


def share_password() -> str:
    return os.environ.get("PLAYGROUND_SHARE_PASSWORD", "").strip()


def share_mode_enabled() -> bool:
    return bool(share_password())


class SharePasswordMiddleware(BaseHTTPMiddleware):
    """HTTP Basic gate so a leaked tunnel URL is not an open playground."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        expected = share_password()
        if not expected:
            return await call_next(request)
        if not _valid_basic(request.headers.get("authorization", ""), expected):
            return PlainTextResponse(
                "請輸入示範通行碼。使用者名稱填 demo，密碼請問分享給你連結的人。",
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="AI Guard demo", charset="UTF-8"'},
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response: Response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault("Cache-Control", "no-store")
        return response


class ChatRateLimiter:
    """Process-wide cap so a public tunnel cannot burn Gemini quota too fast."""

    def __init__(self, max_calls: int = _CHAT_RATE, window_seconds: float = _CHAT_WINDOW_SECONDS) -> None:
        self._max_calls = max_calls
        self._window = window_seconds
        self._hits: list[float] = []
        self._lock = Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            self._hits = [stamp for stamp in self._hits if now - stamp < self._window]
            if len(self._hits) >= self._max_calls:
                return False
            self._hits.append(now)
            return True


def _valid_basic(header: str, expected_password: str) -> bool:
    kind, _, payload = header.partition(" ")
    if kind.lower() != "basic" or not payload:
        return False
    try:
        decoded = base64.b64decode(payload.strip(), validate=True).decode("utf-8")
    except Exception:
        return False
    user, separator, password = decoded.partition(":")
    if separator != ":":
        return False
    user_ok = secrets.compare_digest(user, SHARE_USERNAME)
    pass_ok = secrets.compare_digest(password, expected_password)
    return user_ok and pass_ok
