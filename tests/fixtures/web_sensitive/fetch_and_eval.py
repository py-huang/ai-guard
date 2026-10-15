"""Download Commons fixtures and run Gateway image forbid/redact. Not imported by pytest."""

from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from safety_gateway.gateway import AISafetyGateway
from safety_gateway.pii.ocr import ocr_lines

ROOT = Path(__file__).resolve().parent
ORIGINALS = ROOT / "originals"
UA = "ai-guard-fixture-bot/0.1 (K-12 safety eval; local research)"
COMMONS = "https://commons.wikimedia.org/wiki/Special:FilePath/"


def _font(size: int):
    for path in (
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def download(commons_name: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    url = COMMONS + urllib.parse.quote(commons_name)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, context=ctx, timeout=60) as response:
        dest.write_bytes(response.read())


def stamp(base: Path, dest: Path, text: str) -> None:
    with Image.open(base) as image:
        work = image.convert("RGB")
        draw = ImageDraw.Draw(work)
        font = _font(48)
        draw.rectangle([20, 20, min(work.size[0] - 20, 900), 140], fill=(255, 255, 255))
        draw.text((36, 40), text, fill=(180, 20, 20), font=font)
        dest.parent.mkdir(parents=True, exist_ok=True)
        work.save(dest, format="JPEG", quality=90)


def main() -> None:
    ORIGINALS.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    gateway = AISafetyGateway()
    rows: list[dict[str, object]] = []

    sunflower = ORIGINALS / "_sunflower_base.jpg"
    if not sunflower.exists() or sunflower.stat().st_size < 1000:
        try:
            download("Helianthus_annuus_001.jpg", sunflower)
        except Exception:
            download("Sunflower.jpg", sunflower)

    for item in manifest["items"]:
        dest = ORIGINALS / item["file"]
        if item["id"] == "control_sunflower" and sunflower.exists():
            dest.write_bytes(sunflower.read_bytes())
            item = {**item, "commons": None, "overlay": False}
        expected = item.get("expected")
        error = ""
        try:
            if item.get("overlay"):
                stamps = {
                    "overlay_body_keyword.jpg": "裸照",
                    "overlay_violence_keyword.jpg": "超血腥屍體特寫",
                    "overlay_voyeur_keyword.jpg": "偷拍",
                    "overlay_other_keyword.jpg": "色情",
                }
                stamp(sunflower, dest, stamps[item["file"]])
            elif item.get("commons"):
                if dest.exists() and dest.stat().st_size > 500:
                    pass
                else:
                    download(item["commons"], dest)
        except Exception as exc:
            error = str(exc)
            rows.append(
                {
                    "id": item["id"],
                    "file": item["file"],
                    "expected": expected,
                    "blocked": None,
                    "reason": None,
                    "entities": [],
                    "ocr_preview": "",
                    "hit": False,
                    "error": error,
                    "source": item.get("source"),
                }
            )
            continue

        png = dest.read_bytes()
        ocr = " ".join(ocr_lines(png))[:240]
        result = gateway.redact_image("web-eval", png)
        hit = (result.block_reason == expected) if expected else (result.blocked is False)
        if expected is None:
            hit = result.blocked is False
        rows.append(
            {
                "id": item["id"],
                "file": item["file"],
                "expected": expected,
                "blocked": result.blocked,
                "reason": result.block_reason,
                "entities": result.detected_entities,
                "ocr_preview": ocr.replace("\n", " "),
                "hit": hit,
                "error": "",
                "source": item.get("source"),
            }
        )

    (ROOT / "eval_results.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [
        "# 網路公開圖分類測試結果",
        "",
        "來源以 Wikimedia Commons 為主。不下載真實國民身分證、色情、血腥或偷拍原圖。",
        "第 1、2、3、5 類用同一張向日葵公開圖加上中文關鍵字，只驗證 OCR 攔截路徑。",
        "",
        "| id | 預期類別 | 是否攔截 | 系統原因 | 實體 | 與預期相符 | OCR 摘要 |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        lines.append(
            "| {id} | {expected} | {blocked} | {reason} | {entities} | {hit} | {ocr} |".format(
                id=row["id"],
                expected=row["expected"] or "不應攔（對照）",
                blocked=row["blocked"],
                reason=row["reason"] or row.get("error") or "—",
                entities=", ".join(row["entities"]) if row["entities"] else "—",
                hit="是" if row["hit"] else "否",
                ocr=(row["ocr_preview"] or "—").replace("|", "/"),
            )
        )
    (ROOT / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    ok = sum(1 for row in rows if row["hit"])
    print(f"wrote {len(rows)} rows, hits {ok}/{len(rows)}")


if __name__ == "__main__":
    main()
