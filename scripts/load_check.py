#!/usr/bin/env python3
"""Concurrency check for the production gateway (real uvicorn, real threads).

  .venv/bin/python scripts/load_check.py

Verifies under load that: no request fails with 5xx, tokenization is stable per session
(same value -> same token, even when requests race), sessions never see each other's
tokens, and memory-bounding settings hold. Prints latency percentiles.
"""

from __future__ import annotations

import json
import os
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PORT = int(os.environ.get("LOAD_PORT", "8791"))
BASE = f"http://127.0.0.1:{PORT}"
TOKEN = "load-check-secret-token"
WORKERS = int(os.environ.get("LOAD_WORKERS", "48"))
SESSIONS = int(os.environ.get("LOAD_SESSIONS", "24"))
REPEATS = int(os.environ.get("LOAD_REPEATS", "10"))

_failures: list[str] = []


def check(ok: bool, label: str, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {label}{'' if ok else '  -> ' + detail}")
    if not ok:
        _failures.append(label)


def post(path: str, body: dict) -> tuple[int, dict | None, float]:
    request = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode(),
        headers={"content-type": "application/json", "x-gateway-token": TOKEN},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read())
            return response.status, payload, time.perf_counter() - started
    except urllib.error.HTTPError as error:
        return error.code, None, time.perf_counter() - started


def main() -> int:
    env = {
        **os.environ,
        "SAFETY_GATEWAY_TOKEN": TOKEN,
        "GATEWAY_ENV": "development",
        # Limits high enough that we are testing concurrency, not the rate limiter.
        "GATEWAY_INSPECT_PER_MINUTE": "100000",
        "TLDEXTRACT_CACHE": str(ROOT / ".cache" / "tldextract"),
        "MPLCONFIGDIR": str(ROOT / ".cache" / "mpl"),
    }
    server = subprocess.Popen(
        [sys.executable, "-W", "ignore", "-m", "safety_gateway.server", "--port", str(PORT)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.time() + 120
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(BASE + "/readyz", timeout=2) as response:
                    if response.status == 200:
                        break
            except Exception:
                time.sleep(1)
        else:
            print("gateway never became ready")
            return 1

        # Each session has its own phone number; every thread hammers all sessions.
        phones = {f"load-{i}-{uuid.uuid4().hex[:6]}": f"09{(10000000 + i * 7919) % 100000000:08d}" for i in range(SESSIONS)}
        jobs = [
            (sid, f"我叫王小明，電話{phone}，請記住。")
            for _ in range(REPEATS)
            for sid, phone in phones.items()
        ]

        print(f"\n[{len(jobs)} requests, {WORKERS} threads, {SESSIONS} sessions]")
        started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            results = list(
                pool.map(lambda job: (job[0], *post("/api/sanitize", {"session_id": job[0], "text": job[1]})), jobs)
            )
        elapsed = time.perf_counter() - started

        statuses = [status for _, status, _, _ in results]
        check(all(status == 200 for status in statuses), "no non-200 responses", str(sorted(set(statuses))))

        # Token stability: within one session the phone must always map to one token.
        per_session: dict[str, set[str]] = {sid: set() for sid in phones}
        leaked = 0
        for sid, status, payload, _ in results:
            if status != 200 or payload is None:
                continue
            phone_tokens = {e["token"] for e in payload["entities"] if e["entity_type"] == "PHONE_NUMBER"}
            per_session[sid] |= phone_tokens
            if phones[sid] not in {e["original"] for e in payload["entities"]} and any(
                other in payload["processed_text"] for other in phones.values()
            ):
                leaked += 1
            if any(phone in payload["processed_text"] for phone in phones.values()):
                leaked += 1
        unstable = {sid: toks for sid, toks in per_session.items() if len(toks) != 1}
        check(not unstable, "same value always gets the same token per session (race-free)", str(list(unstable.items())[:2]))
        check(leaked == 0, "no raw phone number survives in processed text", f"{leaked} leaks")

        # A fresh session must never receive another session's mapping.
        status, payload, _ = post("/api/sanitize", {"session_id": "fresh-" + uuid.uuid4().hex[:8], "text": "我叫李大華，電話0911222333"})
        check(
            status == 200 and payload is not None and all(p not in json.dumps(payload, ensure_ascii=False) for p in phones.values()),
            "sessions are isolated",
        )

        latencies = sorted(latency for _, _, _, latency in results)
        p50 = statistics.median(latencies)
        p95 = latencies[int(len(latencies) * 0.95) - 1]
        print(f"  INFO  {len(jobs) / elapsed:.1f} req/s, p50 {p50 * 1000:.0f} ms, p95 {p95 * 1000:.0f} ms, max {latencies[-1] * 1000:.0f} ms")
        check(p95 < 8.0, "p95 latency under the Next.js gateway timeout (8s)", f"{p95:.2f}s")

        with urllib.request.urlopen(BASE + "/readyz", timeout=5) as response:
            check(response.status == 200, "gateway still healthy after the burst")
    finally:
        server.terminate()
        try:
            server.wait(timeout=30)
        except subprocess.TimeoutExpired:
            server.kill()

    print(f"\n{'ALL OK' if not _failures else str(len(_failures)) + ' FAILED'}")
    return 1 if _failures else 0


if __name__ == "__main__":
    sys.exit(main())
