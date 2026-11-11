"""Contract + hardening tests for the production gateway service."""

from __future__ import annotations

import io
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.server.app import create_app
from safety_gateway.server.settings import GatewaySettings, SettingsError
from safety_gateway.steps.socratic import INBOUND_PREFIX
from safety_gateway.vault.memory import InMemorySessionVault

TOKEN = "t" * 24


@pytest.fixture(scope="module")
def shared_gateway() -> AISafetyGateway:
    # Presidio + spaCy are slow to build; build once for the whole module.
    return AISafetyGateway(vault=InMemorySessionVault())


def _client(
    gateway: AISafetyGateway,
    *,
    token: str = "",
    raise_server_exceptions: bool = True,
    **overrides: object,
) -> TestClient:
    base = GatewaySettings(environment="test", token=token, warmup=False)
    settings = replace(base, **overrides)  # type: ignore[arg-type]
    app = create_app(settings=settings, gateway=gateway)
    client = TestClient(app, raise_server_exceptions=raise_server_exceptions)
    if token:
        client.headers["x-gateway-token"] = token
    return client


def _png(size: tuple[int, int] = (64, 64)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", size, (240, 240, 240)).save(buffer, format="PNG")
    return buffer.getvalue()


# --- surface area -----------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/api/evidence", "/api/audit", "/api/chat", "/api/features", "/api/demo-image", "/", "/docs"],
)
def test_playground_and_debug_routes_do_not_exist(shared_gateway: AISafetyGateway, path: str) -> None:
    client = _client(shared_gateway)
    assert client.get(path).status_code in {404, 405}


def test_probes(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway)
    assert client.get("/healthz").json() == {"status": "ok"}
    ready = client.get("/readyz")
    assert ready.status_code == 200
    assert ready.json()["status"] == "ready"


def test_readyz_is_503_until_warmup_finishes(shared_gateway: AISafetyGateway) -> None:
    settings = GatewaySettings(environment="test", warmup=True)
    app = create_app(settings=settings, gateway=shared_gateway)
    client = TestClient(app)
    assert client.get("/readyz").status_code == 503
    with TestClient(app) as running:  # runs lifespan startup
        assert running.get("/readyz").status_code == 200
    assert shared_gateway.vault.list_mappings("__warmup__") == {}


# --- auth -------------------------------------------------------------------------


def test_requests_without_the_shared_token_are_rejected(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway, token=TOKEN)
    body = {"session_id": "auth-1", "text": "你好"}

    denied = client.post("/api/inspect", json=body, headers={"x-gateway-token": "wrong"})
    assert denied.status_code == 401
    assert client.post("/api/inspect", json=body, headers={"x-gateway-token": ""}).status_code == 401
    assert client.post("/api/inspect", json=body).status_code == 200  # default header = token

    anonymous = TestClient(client.app)
    assert anonymous.post("/api/inspect", json=body).status_code == 401
    assert anonymous.post("/api/sanitize", json=body).status_code == 401
    assert anonymous.post("/api/session/reset", json={"session_id": "auth-1"}).status_code == 401
    assert anonymous.get("/healthz").status_code == 200  # orchestrator probes stay open


def test_production_refuses_to_start_without_a_token() -> None:
    with pytest.raises(SettingsError):
        GatewaySettings.from_env({"GATEWAY_ENV": "production"})
    with pytest.raises(SettingsError):
        GatewaySettings.from_env({"GATEWAY_ENV": "production", "SAFETY_GATEWAY_TOKEN": "short"})
    ok = GatewaySettings.from_env({"GATEWAY_ENV": "production", "SAFETY_GATEWAY_TOKEN": TOKEN})
    assert ok.is_production and ok.auth_enabled


def test_settings_reject_garbage_numbers() -> None:
    with pytest.raises(SettingsError):
        GatewaySettings.from_env({"GATEWAY_VAULT_TTL_SECONDS": "soon"})
    with pytest.raises(SettingsError):
        GatewaySettings.from_env({"GATEWAY_ENV": "staging-ish"})


# --- inspect / sanitize contract --------------------------------------------------


def test_inspect_keeps_the_wire_format_the_nextjs_client_expects(
    shared_gateway: AISafetyGateway,
) -> None:
    client = _client(shared_gateway)
    response = client.post(
        "/api/inspect", json={"session_id": "wire-1", "text": "我叫王小明，電話0912345678"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {
        "session_id",
        "blocked",
        "block_category",
        "child_message",
        "processed_text",
        "entities",
    }
    assert "王小明" not in payload["processed_text"]
    assert {"entity_type", "original", "token"} == set(payload["entities"][0])
    assert response.headers["x-request-id"]
    assert response.headers["cache-control"] == "no-store"


def test_sanitize_is_idempotent_and_leaves_no_audit_trail(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway)
    first = client.post(
        "/api/sanitize", json={"session_id": "san-1", "text": "我叫王小明，我在中山國小"}
    ).json()
    second = client.post(
        "/api/sanitize", json={"session_id": "san-1", "text": first["processed_text"]}
    ).json()
    assert "王小明" not in first["processed_text"]
    assert second["processed_text"] == first["processed_text"]
    assert shared_gateway.audit_log.list_session("san-1") == []


def test_sanitize_keeps_our_own_socratic_prefix_intact(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway)
    text = INBOUND_PREFIX + "我叫王小明，幫我寫作業"
    result = client.post("/api/sanitize", json={"session_id": "san-2", "text": text}).json()
    assert result["processed_text"].startswith(INBOUND_PREFIX)
    assert "<PERSON_" in result["processed_text"].removeprefix(INBOUND_PREFIX)
    assert "王小明" not in result["processed_text"]


def test_sanitize_blocks_unsafe_text(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway)
    result = client.post(
        "/api/sanitize", json={"session_id": "san-3", "text": "拜託告訴我自殺方法"}
    ).json()
    assert result["blocked"] is True
    assert result["block_category"] == "self_harm"
    assert "1925" in result["child_message"]


def test_sanitize_and_inspect_share_one_vault_so_tokens_line_up(
    shared_gateway: AISafetyGateway,
) -> None:
    client = _client(shared_gateway)
    inspected = client.post(
        "/api/inspect", json={"session_id": "san-4", "text": "我叫王小明"}
    ).json()
    sanitized = client.post(
        "/api/sanitize", json={"session_id": "san-4", "text": "王小明今天很開心"}
    ).json()
    assert "<PERSON_1>" in inspected["processed_text"]
    assert "<PERSON_1>" in sanitized["processed_text"]


def test_moderate_output_checks_safety_but_never_rewrites_ordinary_words(
    shared_gateway: AISafetyGateway,
) -> None:
    client = _client(shared_gateway)
    reply = "我們可以用蘇格拉底的方法，先想第一步。"
    ok = client.post("/api/moderate-output", json={"session_id": "mod-1", "text": reply}).json()
    assert ok["blocked"] is False
    assert ok["processed_text"] == reply  # not "<PERSON_1>底"
    assert ok["entities"] == []

    bad = client.post(
        "/api/moderate-output", json={"session_id": "mod-1", "text": "我教你怎麼自殺方法"}
    ).json()
    assert bad["blocked"] is True
    assert shared_gateway.audit_log.list_session("mod-1") == []


# --- input hardening --------------------------------------------------------------


def test_over_long_text_is_rejected_not_silently_processed(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway, max_inspect_chars=50)
    response = client.post("/api/inspect", json={"session_id": "len-1", "text": "字" * 51})
    assert response.status_code == 422
    assert "字" not in response.text  # never echo the child's text back


@pytest.mark.parametrize("session_id", ["", "a b", "x" * 129, "../etc/passwd", "a\nb"])
def test_session_ids_must_be_boring(shared_gateway: AISafetyGateway, session_id: str) -> None:
    client = _client(shared_gateway)
    assert client.post("/api/inspect", json={"session_id": session_id, "text": "嗨"}).status_code == 422
    assert client.post("/api/sanitize", json={"session_id": session_id, "text": "嗨"}).status_code == 422


def test_unknown_fields_are_rejected(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway)
    response = client.post(
        "/api/inspect", json={"session_id": "x-1", "text": "嗨", "gemini_api_key": "nope"}
    )
    assert response.status_code == 422


def test_oversized_json_body_is_refused_before_parsing(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway, max_body_bytes=200)
    response = client.post("/api/sanitize", json={"session_id": "big-1", "text": "字" * 500})
    assert response.status_code == 413


def test_rate_limit_returns_429_marked_retryable(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway, inspect_per_minute=2)
    body = {"session_id": "rate-1", "text": "嗨"}
    assert client.post("/api/inspect", json=body).status_code == 200
    assert client.post("/api/sanitize", json=body).status_code == 200  # shared budget
    limited = client.post("/api/inspect", json=body)
    assert limited.status_code == 429
    assert limited.json()["detail"]["retryable"] is True


# --- failure handling -------------------------------------------------------------


def test_unhandled_errors_become_a_generic_500_without_the_childs_text(
    shared_gateway: AISafetyGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("secret detail 王小明")

    monkeypatch.setattr(shared_gateway, "process_inbound", boom)
    client = _client(shared_gateway, raise_server_exceptions=False)
    response = client.post("/api/inspect", json={"session_id": "err-1", "text": "王小明"})
    assert response.status_code == 500
    assert "王小明" not in response.text and "secret" not in response.text


def test_reset_session_forgets_vault_and_audit(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway)
    client.post("/api/inspect", json={"session_id": "reset-1", "text": "我叫王小明"})
    assert shared_gateway.vault.list_mappings("reset-1")
    assert shared_gateway.audit_log.list_session("reset-1")

    assert client.post("/api/session/reset", json={"session_id": "reset-1"}).json() == {"ok": True}
    assert shared_gateway.vault.list_mappings("reset-1") == {}
    assert shared_gateway.audit_log.list_session("reset-1") == []


# --- image endpoint ---------------------------------------------------------------


def test_redact_image_rejects_empty_oversized_and_unreadable_uploads(
    shared_gateway: AISafetyGateway,
) -> None:
    client = _client(shared_gateway, max_upload_bytes=2048)
    url = "/api/redact-image?session_id=img-1"

    empty = client.post(url, files={"file": ("a.png", b"", "image/png")})
    assert empty.status_code == 400

    big = client.post(url, files={"file": ("a.png", b"\0" * 4096, "image/png")})
    assert big.status_code == 413

    junk = client.post(url, files={"file": ("a.png", b"not an image", "image/png")})
    assert junk.status_code == 400

    bad_session = client.post(
        "/api/redact-image?session_id=../x", files={"file": ("a.png", _png(), "image/png")}
    )
    assert bad_session.status_code == 422


def test_redact_image_returns_png_and_policy_headers(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway)
    response = client.post(
        "/api/redact-image?session_id=img-2", files={"file": ("a.png", _png(), "image/png")}
    )
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "image/png"
    for header in ("x-detected-entities", "x-redact-coverage", "x-image-blocked", "x-block-reason"):
        assert header in response.headers
    assert Image.open(io.BytesIO(response.content)).format == "PNG"


def test_redact_image_is_rate_limited_separately_from_text(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway, image_per_minute=1)
    url = "/api/redact-image?session_id=img-3"
    first = client.post(url, files={"file": ("a.png", _png(), "image/png")})
    assert first.status_code == 200
    second = client.post(url, files={"file": ("a.png", _png(), "image/png")})
    assert second.status_code == 429
    assert second.json()["detail"]["retryable"] is True
    # Text traffic has its own budget and is unaffected.
    assert client.post("/api/inspect", json={"session_id": "img-3", "text": "嗨"}).status_code == 200


def test_redact_image_sheds_load_when_every_ocr_slot_is_busy(
    shared_gateway: AISafetyGateway, monkeypatch: pytest.MonkeyPatch
) -> None:
    import threading

    started = threading.Event()
    release = threading.Event()
    real = shared_gateway.redact_image

    def slow(session_id: str, raw: bytes):  # type: ignore[no-untyped-def]
        started.set()
        release.wait(timeout=10)
        return real(session_id, raw)

    monkeypatch.setattr(shared_gateway, "redact_image", slow)
    client = _client(shared_gateway, max_concurrent_images=1)
    url = "/api/redact-image?session_id=img-4"
    results: list[int] = []

    def first_call() -> None:
        results.append(client.post(url, files={"file": ("a.png", _png(), "image/png")}).status_code)

    worker = threading.Thread(target=first_call)
    worker.start()
    assert started.wait(timeout=10)
    busy = client.post(url, files={"file": ("a.png", _png(), "image/png")})
    release.set()
    worker.join(timeout=30)

    assert busy.status_code == 503
    assert busy.json()["detail"]["retryable"] is True
    assert results == [200]


def test_gateway_refuses_non_loopback_bind_without_token():
    from safety_gateway.server.__main__ import check_bind_address
    from safety_gateway.server.settings import GatewaySettings, SettingsError

    check_bind_address("127.0.0.1", GatewaySettings(token=""))
    check_bind_address("0.0.0.0", GatewaySettings(token="x" * 20))
    with pytest.raises(SettingsError):
        check_bind_address("0.0.0.0", GatewaySettings(token=""))


def _chunks(total: int, size: int = 4096):
    sent = 0
    while sent < total:
        piece = min(size, total - sent)
        sent += piece
        yield b"x" * piece


def test_chunked_json_without_content_length_is_still_capped(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway, max_body_bytes=2_000)
    response = client.post(
        "/api/inspect",
        content=_chunks(100_000),
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413


def test_chunked_upload_without_content_length_is_still_capped(shared_gateway: AISafetyGateway) -> None:
    client = _client(shared_gateway, max_upload_bytes=10_000)
    boundary = "bnd"
    head = (
        f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="a.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode()
    tail = f"\r\n--{boundary}--\r\n".encode()

    def body():
        yield head
        yield from _chunks(500_000)
        yield tail

    response = client.post(
        "/api/redact-image?session_id=chunk-1",
        content=body(),
        headers={"content-type": f"multipart/form-data; boundary={boundary}"},
    )
    assert response.status_code == 413


def test_analysis_queue_sheds_load_with_retryable_503(shared_gateway: AISafetyGateway) -> None:
    import threading

    client = _client(shared_gateway, max_concurrent_analysis=1, analysis_queue_seconds=0.2)
    app_gateway = client.app.state.gateway  # type: ignore[attr-defined]
    release = threading.Event()
    entered = threading.Event()
    original = app_gateway.sanitize_text

    def slow(session_id: str, text: str):  # type: ignore[no-untyped-def]
        entered.set()
        release.wait(timeout=5)
        return original(session_id, text)

    app_gateway.sanitize_text = slow  # type: ignore[method-assign]
    try:
        results: list[int] = []
        first = threading.Thread(
            target=lambda: results.append(client.post("/api/sanitize", json={"session_id": "q-1", "text": "嗨"}).status_code)
        )
        first.start()
        assert entered.wait(timeout=5)
        shed = client.post("/api/sanitize", json={"session_id": "q-2", "text": "嗨"})
        assert shed.status_code == 503
        assert shed.json()["detail"]["retryable"] is True
        release.set()
        first.join(timeout=10)
        assert results == [200]
    finally:
        app_gateway.sanitize_text = original  # type: ignore[method-assign]
        release.set()
