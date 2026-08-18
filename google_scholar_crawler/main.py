#!/usr/bin/env python3
"""Fetch Google Scholar citation stats and write the files the site uses.

Google Scholar has no public API, so this job scrapes the public author
profile. The scholarly library is tried first because it already works on
GitHub-hosted runners; a single-page HTML parse is the fallback.
Failed fetches leave the previously committed files in place.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from parse import author_from_scholarly, is_plausible, parse_author_profile

ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = ROOT / "assets" / "results"
PROFILE_YML = ROOT / "_data" / "profile.yml"
JEKYLL_DATA = ROOT / "_data" / "google_scholar.json"
GS_DATA_PATH = RESULTS_DIR / "gs_data.json"
SHIELDS_PATH = RESULTS_DIR / "gs_data_shieldsio.json"

SCHOLAR_ID_RE = re.compile(r"^gscholar:\s*['\"]?([A-Za-z0-9_-]+)", re.MULTILINE)
PROFILE_URL = (
    "https://scholar.google.com/citations?user={id}&hl=en&cstart=0&pagesize=100"
)
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
RETRIES = 4


def scholar_id() -> str:
    env_id = os.environ.get("GOOGLE_SCHOLAR_ID", "").strip()
    if env_id:
        return env_id
    text = PROFILE_YML.read_text(encoding="utf-8")
    match = SCHOLAR_ID_RE.search(text)
    if not match:
        raise SystemExit("Could not find gscholar id in _data/profile.yml")
    return match.group(1)


def load_previous() -> dict[str, Any] | None:
    if not GS_DATA_PATH.exists():
        return None
    try:
        return json.loads(GS_DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def previous_citedby(previous: dict[str, Any] | None) -> int | None:
    if not previous:
        return None
    value = previous.get("citedby")
    return int(value) if isinstance(value, int) else None


def fetch_via_html(sid: str) -> dict[str, Any]:
    response = requests.get(
        PROFILE_URL.format(id=sid),
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml",
        },
        timeout=30,
    )
    response.raise_for_status()
    author = parse_author_profile(response.text, sid)
    author["fetched_via"] = "html"
    return author


def fetch_via_scholarly(sid: str) -> dict[str, Any]:
    from scholarly import scholarly

    raw = scholarly.search_author_id(sid)
    scholarly.fill(raw, sections=["basics", "indices", "counts", "publications"])
    author = author_from_scholarly(raw)
    author["fetched_via"] = "scholarly"
    return author


def fetch_author(sid: str) -> dict[str, Any]:
    errors: list[str] = []
    # scholarly is the path that already succeeds on GitHub-hosted runners.
    # A single-page HTML scrape is the fallback if scholarly cannot import or fill.
    for attempt in range(1, RETRIES + 1):
        for fetcher in (fetch_via_scholarly, fetch_via_html):
            try:
                print(f"[{attempt}/{RETRIES}] trying {fetcher.__name__}", flush=True)
                return fetcher(sid)
            except Exception as exc:
                errors.append(f"{fetcher.__name__} attempt {attempt}: {exc}")
                print(errors[-1], file=sys.stderr, flush=True)
        if attempt < RETRIES:
            wait = min(2 ** attempt, 30)
            print(f"retrying in {wait}s", flush=True)
            time.sleep(wait)
    raise RuntimeError("All Google Scholar fetches failed:\n" + "\n".join(errors))


def write_outputs(author: dict[str, Any]) -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    JEKYLL_DATA.parent.mkdir(parents=True, exist_ok=True)
    author["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    GS_DATA_PATH.write_text(
        json.dumps(author, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    SHIELDS_PATH.write_text(
        json.dumps(
            {
                "schemaVersion": 1,
                "label": "citations",
                "message": str(author["citedby"]),
                "cacheSeconds": 86400,
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    publications = author.get("publications") or []
    slim = {
        "citedby": author["citedby"],
        "hindex": author.get("hindex"),
        "i10index": author.get("i10index"),
        "updated": author["updated"],
        "scholar_id": author["scholar_id"],
        "publications": publications,
        "by_id": {
            pub["id"]: pub
            for pub in publications
            if pub.get("id")
        },
    }
    JEKYLL_DATA.write_text(
        json.dumps(slim, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    sid = scholar_id()
    previous = load_previous()
    old_citedby = previous_citedby(previous)
    print(f"Fetching Google Scholar profile {sid}", flush=True)

    try:
        author = fetch_author(sid)
    except Exception:
        traceback.print_exc()
        print("Keeping previously committed citation files.", flush=True)
        return 1

    new_citedby = author["citedby"]
    if not is_plausible(new_citedby, old_citedby):
        print(
            f"Refusing to write implausible citedby={new_citedby} "
            f"(previous={old_citedby})",
            file=sys.stderr,
        )
        return 1

    write_outputs(author)
    print(
        f"Wrote citation data: citedby={new_citedby} "
        f"(was {old_citedby}), via {author.get('fetched_via')}, "
        f"{len(author.get('publications') or [])} publications",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
