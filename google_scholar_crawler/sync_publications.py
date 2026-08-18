"""Sync `_publications` markdown files with crawled Google Scholar papers.

Curated pages keep their authors, links, badges, and dates. New Scholar papers
are added in the same Jekyll front-matter format. Existing files that only
lack `scholar_pub_id` get that field inserted.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import yaml

from parse import normalize_title

FRONT_MATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
SCHOLAR_ID_LINE_RE = re.compile(r"^scholar_pub_id:", re.M)
PUB_DATE_LINE_RE = re.compile(r"^(pub_date:.*)$", re.M)
GENERATED_MARKER = "generated:      true"


def sync_publications(publications_dir: Path, author: dict[str, Any]) -> dict[str, list[str]]:
    papers = [pub for pub in (author.get("publications") or []) if pub.get("id") and pub.get("title")]
    locals_ = load_local_publications(publications_dir)

    created: list[str] = []
    updated: list[str] = []
    linked: list[str] = []
    used: set[Path] = set()

    for paper in papers:
        match = match_local(paper, locals_, used)
        if match is None:
            path = write_generated_page(publications_dir, paper)
            created.append(str(path.relative_to(publications_dir)))
            continue

        path, meta, original = match
        used.add(path)
        if meta.get("generated") is True:
            write_generated_page(publications_dir, paper, path=path)
            updated.append(str(path.relative_to(publications_dir)))
            continue
        if not meta.get("scholar_pub_id"):
            if insert_scholar_pub_id(path, original, paper["id"]):
                linked.append(str(path.relative_to(publications_dir)))

    return {"created": created, "updated": updated, "linked": linked}


def load_local_publications(publications_dir: Path) -> list[tuple[Path, dict[str, Any], str]]:
    items = []
    if not publications_dir.exists():
        return items
    for path in sorted(publications_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        match = FRONT_MATTER_RE.match(text)
        if not match:
            continue
        meta = yaml.safe_load(match.group(1)) or {}
        items.append((path, meta, text))
    return items


def match_local(
    paper: dict[str, Any],
    locals_: list[tuple[Path, dict[str, Any], str]],
    used: set[Path],
) -> tuple[Path, dict[str, Any], str] | None:
    pub_id = paper.get("id")
    for path, meta, text in locals_:
        if path in used:
            continue
        if meta.get("scholar_pub_id") == pub_id:
            return path, meta, text
        aliases = meta.get("scholar_pub_ids") or []
        if isinstance(aliases, list) and pub_id in aliases:
            return path, meta, text
    target = normalize_title(paper.get("title"))
    if not target:
        return None
    for path, meta, text in locals_:
        if path in used or meta.get("scholar_pub_id"):
            continue
        if normalize_title(str(meta.get("title") or "")) == target:
            return path, meta, text
    return None


def insert_scholar_pub_id(path: Path, original: str, pub_id: str) -> bool:
    if SCHOLAR_ID_LINE_RE.search(original):
        return False

    def replacer(match: re.Match[str]) -> str:
        front = match.group(1)
        line = f'scholar_pub_id: "{pub_id}"'
        if PUB_DATE_LINE_RE.search(front):
            front = PUB_DATE_LINE_RE.sub(r"\1\n" + line, front, count=1)
        else:
            front = front.rstrip() + "\n" + line
        return f"---\n{front}\n---"

    updated, count = FRONT_MATTER_RE.subn(replacer, original, count=1)
    if count != 1 or updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def write_generated_page(
    publications_dir: Path,
    paper: dict[str, Any],
    path: Path | None = None,
) -> Path:
    year = str(paper.get("year") or "").strip()
    if not re.fullmatch(r"\d{4}", year):
        year = "undated"
    if path is None:
        folder = publications_dir / year
        folder.mkdir(parents=True, exist_ok=True)
        path = unique_path(folder, f"{year}-{slugify(paper['title'])}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_generated_markdown(paper), encoding="utf-8")
    return path


def unique_path(folder: Path, filename: str) -> Path:
    candidate = folder / filename
    if not candidate.exists():
        return candidate
    stem = candidate.stem
    suffix = candidate.suffix
    for index in range(2, 50):
        alt = folder / f"{stem}-{index}{suffix}"
        if not alt.exists():
            return alt
    return folder / f"{stem}-new{suffix}"


def slugify(title: str, max_length: int = 70) -> str:
    text = re.sub(r"<[^>]+>", " ", title or "")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    text = text[:max_length].strip("-")
    return text or "publication"


def render_generated_markdown(paper: dict[str, Any]) -> str:
    title = str(paper.get("title") or "Untitled").strip()
    year = str(paper.get("year") or "").strip()
    if not re.fullmatch(r"\d{4}", year):
        year = "2020"
    venue = str(paper.get("venue") or "").strip()
    arxiv_id = paper.get("arxiv_id")
    if arxiv_id and not venue:
        venue = "arXiv"
    authors = [str(name).strip() for name in (paper.get("authors") or []) if str(name).strip()]
    pub_id = paper["id"]

    lines = [
        "---",
        field("title", f"<strong>{escape_html(title)}</strong>"),
        field("date", f"{year}-01-15 00:01:00 +0800"),
        field("selected", "false"),
    ]
    if venue:
        lines.append(field("pub", venue))
    if arxiv_id or (venue.lower() == "arxiv"):
        lines.append(
            "pub_last:       ' <span class=\"badge badge-pill badge-custom badge-secondary\">Preprint</span>'"
        )
    lines.extend(
        [
            field("pub_date", year),
            field("scholar_pub_id", pub_id),
            "# Auto-updated from Google Scholar. Set generated: false to keep manual edits.",
            GENERATED_MARKER,
            "",
        ]
    )
    if authors:
        lines.append("authors:")
        for name in authors:
            lines.append(f"  - {name}")

    links = {}
    if arxiv_id:
        links["Paper"] = f"https://doi.org/10.48550/arXiv.{arxiv_id.split('v')[0]}"
    if links:
        lines.append("links:")
        for label, url in links.items():
            lines.append(f"  {label}: {url}")
    lines.append("---\n")
    return "\n".join(lines)


def field(key: str, value: str) -> str:
    if key in {"selected", "date"}:
        rendered = value
    else:
        rendered = json.dumps(value, ensure_ascii=False)
    return f"{key + ':':<16}{rendered}"


def escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
