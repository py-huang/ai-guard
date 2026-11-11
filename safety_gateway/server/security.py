"""Edge guards for the production gateway: auth, size cap, request id, access log."""

from __future__ import annotations

import secrets
import time
from collections import deque
from threading import Lock
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from safety_gateway.obs import get_logger
from safety_gateway.server.settings import GatewaySettings

TOKEN_HEADER = "x-gateway-token"
REQUEST_ID_HEADER = "x-request-id"

# Liveness / readiness must be reachable by an orchestrator that has no secret.
_PUBLIC_PATHS = frozenset({"/healthz", "/readyz"})
# Routes that legitimately receive a multipart image instead of a small JSON body.
_UPLOAD_PATHS = frozenset({"/api/redact-image"})

_logger = get_logger()


def error_response(status: int, message: str, *, retryable: bool = False) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={"detail": {"message": message, "retryable": retryable}},
        headers={"Cache-Control": "no-store"},
    )


class SlidingWindowLimiter:
    """Process-wide sliding-window counter. Cheap, thread-safe, no dependencies."""

    def __init__(self, max_calls: int, window_seconds: float = 60.0) -> None:
        self._max_calls = max_calls
        self._window = window_seconds
        self._hits: deque[float] = deque()
        self._lock = Lock()

    def allow(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._hits and now - self._hits[0] >= self._window:
                self._hits.popleft()
            if len(self._hits) >= self._max_calls:
                return False
            self._hits.append(now)
            return True


class _BodyTooLarge(Exception):
    pass


class BodyLimitMiddleware:
    """Cap request bodies on the byte stream, not just on the Content-Length header.

    A chunked request carries no Content-Length, and Starlette spools multipart uploads to
    disk before a handler can look at them. Counting bytes as they arrive stops both.
    Pure ASGI on purpose: it must sit *inside* the guard middleware (so refusals are
    logged) and see the raw receive channel.
    """

    def __init__(self, app, settings: GatewaySettings) -> None:  # type: ignore[no-untyped-def]
        self.app = app
        self._settings = settings

    def _limit_for(self, path: str) -> int:
        if path in _UPLOAD_PATHS:
            return self._settings.max_upload_bytes + 64_000
        return self._settings.max_body_bytes

    async def __call__(self, scope, receive, send):  # type: ignore[no-untyped-def]
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        limit = self._limit_for(scope["path"])
        declared = dict(scope["headers"]).get(b"content-length")
        if declared is not None:
            if not declared.isdigit():
                await self._reply(send, 400, "bad content-length")
                return
            if int(declared) > limit:
                await self._reply(send, 413, "payload too large")
                return

        state = {"seen": 0, "exceeded": False, "responded": False}

        async def limited_receive():  # type: ignore[no-untyped-def]
            message = await receive()
            if message["type"] == "http.request":
                state["seen"] += len(message.get("body", b""))
                if state["seen"] > limit:
                    state["exceeded"] = True
                    raise _BodyTooLarge
            return message

        async def guarded_send(message):  # type: ignore[no-untyped-def]
            # FastAPI turns any body-read exception into a 400; once we cut the stream the
            # only honest answer is 413, so replace whatever the app tried to say.
            if state["exceeded"]:
                if not state["responded"]:
                    state["responded"] = True
                    await self._reply(send, 413, "payload too large")
                return
            if message["type"] == "http.response.start":
                state["responded"] = True
            await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except _BodyTooLarge:
            if not state["responded"]:
                state["responded"] = True
                await self._reply(send, 413, "payload too large")

    @staticmethod
    async def _reply(send, status: int, message: str) -> None:  # type: ignore[no-untyped-def]
        response = error_response(status, message)
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(response.body)).encode()),
                    (b"cache-control", b"no-store"),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": response.body})


class GatewayGuardMiddleware(BaseHTTPMiddleware):
    """Request id + shared-secret auth + body-size cap + one PII-free access-log line."""

    def __init__(self, app, settings: GatewaySettings) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._settings = settings

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        request_id = _clean_request_id(request.headers.get(REQUEST_ID_HEADER)) or uuid4().hex
        request.state.request_id = request_id
        path = request.url.path

        rejected = self._reject(request, path)
        if rejected is not None:
            response: Response = rejected
        else:
            response = await call_next(request)

        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers.setdefault("Cache-Control", "no-store")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        _logger.info(
            "request",
            extra={
                "event": "request",
                "request_id": request_id,
                "method": request.method,
                "path": path,  # path only: query strings carry session ids
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        )
        return response

    def _reject(self, request: Request, path: str) -> Response | None:
        if path not in _PUBLIC_PATHS and self._settings.auth_enabled:
            supplied = request.headers.get(TOKEN_HEADER, "")
            if not secrets.compare_digest(
                supplied.encode("utf-8"), self._settings.token.encode("utf-8")
            ):
                return error_response(401, "unauthorized")
        return None


def _clean_request_id(value: str | None) -> str:
    if not value:
        return ""
    cleaned = "".join(ch for ch in value if ch.isalnum() or ch in "-_")[:64]
    return cleaned
