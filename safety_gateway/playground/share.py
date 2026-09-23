"""Temporary HTTPS tunnel to 127.0.0.1 playground (ngrok, or Cloudflare if ngrok is missing)."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

_CLOUDFLARED_URL = (
    "https://github.com/cloudflare/cloudflared/releases/download/"
    "2026.9.0/cloudflared-darwin-arm64.tgz"
)
_URL_RE = re.compile(r"https://[a-z0-9.-]+\.(ngrok-free\.app|ngrok\.io|trycloudflare\.com)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="把本機 127.0.0.1 服務打成暫時 HTTPS（playground 或 Next 主專案）"
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    password = os.environ.get("PLAYGROUND_SHARE_PASSWORD", "").strip()
    if args.port == 8765 and not password:
        print(
            "分享 playground 時請先設 PLAYGROUND_SHARE_PASSWORD 再重啟 8765。\n"
            "分享 Next 主專案請用 --port 3001（正式版）或 --port 3000。",
            file=sys.stderr,
        )
        raise SystemExit(2)
    if not _port_open(args.port):
        print(f"127.0.0.1:{args.port} 沒有在聽。請先開本機服務。", file=sys.stderr)
        raise SystemExit(2)

    if password and args.port == 8765:
        print("通行碼使用者名稱：demo")
        print(f"通行碼：{password}")
        print("只傳給要試用的人。用完請 Ctrl+C 停隧道。")
    else:
        print(f"分享 Next 主專案 → http://127.0.0.1:{args.port}")
        print("用完請 Ctrl+C 停隧道。")
    print()

    ngrok = shutil.which("ngrok")
    if ngrok:
        _run_ngrok(ngrok, args.port)
        return
    _run_cloudflared(args.port)


def _port_open(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _run_ngrok(binary: str, port: int) -> None:
    print(f"使用 ngrok → http://127.0.0.1:{port}")
    process = subprocess.Popen(
        [binary, "http", f"127.0.0.1:{port}", "--log=stdout", "--log-format=term"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    _stream_until_url(process, "ngrok")


def _run_cloudflared(port: int) -> None:
    binary = _ensure_cloudflared()
    print(f"本機沒有 ngrok，改用 Cloudflare 快速隧道 → http://127.0.0.1:{port}")
    process = subprocess.Popen(
        [str(binary), "tunnel", "--url", f"http://127.0.0.1:{port}", "--no-autoupdate"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    _stream_until_url(process, "cloudflared")


def _ensure_cloudflared() -> Path:
    target = Path(sys.prefix) / "bin" / "cloudflared-share"
    if target.is_file() and os.access(target, os.X_OK):
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    print("下載 cloudflared（只放在虛擬環境，不當系統安裝）…")
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "cloudflared.tgz"
        urllib.request.urlretrieve(_CLOUDFLARED_URL, archive)
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(tmp, filter="data")
        extracted = Path(tmp) / "cloudflared"
        if not extracted.is_file():
            raise RuntimeError("cloudflared archive did not contain a binary")
        shutil.copy2(extracted, target)
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
    return target


def _stream_until_url(process: subprocess.Popen[str], name: str) -> None:
    assert process.stdout is not None
    found = False
    try:
        for line in process.stdout:
            sys.stdout.write(line)
            sys.stdout.flush()
            match = _URL_RE.search(line)
            if match and not found:
                found = True
                print()
                print(f"分享網址：{match.group(0)}")
                print("用瀏覽器打開即可。若是 playground 會再要 demo + 通行碼。")
                print()
        process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        print(f"\n已停止 {name} 隧道。")
        raise SystemExit(0) from None
    if process.returncode not in (0, None):
        raise SystemExit(process.returncode or 1)


if __name__ == "__main__":
    main()
