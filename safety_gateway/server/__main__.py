from __future__ import annotations

import argparse

import uvicorn

from safety_gateway.server.settings import GatewaySettings, SettingsError


_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def check_bind_address(host: str, settings: GatewaySettings) -> None:
    """Refuse to listen beyond loopback without the shared secret (dev mode allows no token)."""
    if host not in _LOOPBACK_HOSTS and not settings.token:
        raise SettingsError(
            f"refusing to bind {host!r} without SAFETY_GATEWAY_TOKEN; "
            "set a token or bind 127.0.0.1"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="AI Guard Safety Gateway (production service)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    try:
        # Fail fast, before models load, if the environment is unsafe for this mode.
        settings = GatewaySettings.from_env()
        check_bind_address(args.host, settings)
    except SettingsError as exc:
        raise SystemExit(f"configuration error: {exc}") from exc
    uvicorn.run(
        "safety_gateway.server.app:create_app",
        factory=True,
        host=args.host,
        port=args.port,
        reload=False,
        # Structured access logs come from our middleware; uvicorn's would add the query string.
        access_log=False,
        timeout_graceful_shutdown=15,
    )


if __name__ == "__main__":
    main()
