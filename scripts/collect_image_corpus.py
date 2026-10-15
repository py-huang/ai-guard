#!/usr/bin/env python3
"""Download public-domain / CC Wikimedia images for the five child-forbid categories.

Does not scrape porn, gore shock sites, voyeurism, or living people's Taiwan IDs.
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "image-corpus"
USER_AGENT = "ai-guard-corpus/0.1 (local child-safety eval; educational)"

# 20+ search hits per category; File: namespace = 6.
SEARCHES: dict[str, list[str]] = {
    "01-body": [
        "nude painting venus",
        "nude sculpture marble",
        "academic nude drawing",
    ],
    "02-violence": [
        "battle painting war",
        "wounded soldier painting",
        "sword fight painting",
    ],
    "03-voyeur": [
        "hidden camera device",
        "security peephole door",
        "spy camera product",
        "CCTV camera indoor",
        "door viewer peephole",
        "surveillance camera ceiling",
        "webcam privacy",
    ],
    "04-document": [
        "credit card visa",
        "passport biodata page specimen",
        "driver license card",
        "identity card european",
    ],
    "05-other": [
        "cigarette advertising poster",
        "casino chips gambling",
        "beer advertisement vintage",
        "whisky advertisement",
        "slot machine casino",
        "tobacco pack warning",
    ],
}


def commons_search(query: str, limit: int = 12) -> list[dict[str, str]]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|mime|size",
        "iiurlwidth": "1280",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    pages = (payload.get("query") or {}).get("pages") or {}
    found: list[dict[str, str]] = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        mime = str(info.get("mime") or "")
        if mime not in {"image/jpeg", "image/png", "image/gif", "image/webp"}:
            continue
        thumb = info.get("thumburl") or info.get("url")
        title = str(page.get("title") or "file")
        if not thumb:
            continue
        found.append({"title": title, "url": thumb, "mime": mime})
    return found


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read()
        if len(data) < 2000:
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        return False


def collect_category(category: str, queries: list[str], minimum: int = 20) -> list[dict[str, str]]:
    folder = ROOT / category
    folder.mkdir(parents=True, exist_ok=True)
    seen_titles: set[str] = set()
    saved: list[dict[str, str]] = []
    existing = sorted(p for p in folder.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"})
    index = len(existing) + 1
    if index > 1 and index - 1 >= minimum:
        return [
            {"file": str(path.relative_to(ROOT.parent.parent.parent)), "source_title": path.name, "source_url": "", "query": "existing", "category": category}
            for path in existing
        ]
    for query in queries:
        if len(saved) >= minimum:
            break
        time.sleep(0.4)
        for item in commons_search(query, limit=15):
            if item["title"] in seen_titles:
                continue
            seen_titles.add(item["title"])
            ext = ".jpg" if "jpeg" in item["mime"] else ".png"
            name = f"{index:02d}{ext}"
            path = folder / name
            if download(item["url"], path):
                saved.append(
                    {
                        "file": str(path.relative_to(ROOT.parent.parent.parent)),
                        "source_title": item["title"],
                        "source_url": item["url"],
                        "query": query,
                        "category": category,
                    }
                )
                index += 1
            if len(saved) >= minimum:
                break
    return saved


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, str]] = []
    for category, queries in SEARCHES.items():
        print(f"collecting {category}...")
        manifest.extend(collect_category(category, queries, minimum=20))
        print(f"  saved {sum(1 for item in manifest if item['category'] == category)}")
    (ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print("wrote", ROOT / "manifest.json", "total", len(manifest))


if __name__ == "__main__":
    main()
