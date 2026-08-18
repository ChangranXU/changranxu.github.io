"""Parse Google Scholar author-profile HTML into citation stats."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

_CITATION_FOR_VIEW_RE = re.compile(r"citation_for_view=([\w:-]+)")
_INT_RE = re.compile(r"[^\d]")
_ARXIV_RE = re.compile(r"arxiv(?:\.org/abs/|:?\s*)(\d{4}\.\d{4,5}(?:v\d+)?)", re.I)


def parse_int(text: str | None) -> int:
    if text is None:
        return 0
    digits = _INT_RE.sub("", str(text))
    return int(digits) if digits else 0


def parse_author_profile(html: str, scholar_id: str) -> dict[str, Any]:
    """Extract citation totals, indices, and papers from an author profile page.

    Google Scholar has no public API. The author page exposes:
      - ``td.gsc_rsb_std``: Citations / h-index / i10-index (all and 5-year)
      - ``tr.gsc_a_tr``: publication rows (use ``pagesize=100`` to avoid paging)
    """
    soup = BeautifulSoup(html, "html.parser")

    captcha = soup.find(id="gs_captcha_ccl") or soup.find(id="recaptcha")
    if captcha:
        raise ValueError("Google Scholar returned a CAPTCHA page")

    name_el = soup.find("div", id="gsc_prf_in")
    if name_el is None:
        raise ValueError("Not a Google Scholar author profile (missing name)")

    index = soup.find_all("td", class_="gsc_rsb_std")
    if len(index) < 6:
        raise ValueError("Citation stats table missing from author profile")

    citedby = parse_int(index[0].get_text())
    publications = _parse_publications(soup)

    affiliation_el = soup.find("div", class_="gsc_prf_il")
    return {
        "scholar_id": scholar_id,
        "name": name_el.get_text(strip=True),
        "affiliation": affiliation_el.get_text(strip=True) if affiliation_el else "",
        "citedby": citedby,
        "citedby5y": parse_int(index[1].get_text()),
        "hindex": parse_int(index[2].get_text()),
        "hindex5y": parse_int(index[3].get_text()),
        "i10index": parse_int(index[4].get_text()),
        "i10index5y": parse_int(index[5].get_text()),
        "cites_per_year": _parse_cites_per_year(soup),
        "publications": publications,
    }


def author_from_scholarly(author: dict[str, Any]) -> dict[str, Any]:
    """Normalize a scholarly Author object into the compact schema."""
    citedby = author.get("citedby")
    if citedby is None:
        raise ValueError("scholarly response is missing citedby")

    raw_pubs = author.get("publications") or []
    if isinstance(raw_pubs, dict):
        raw_pubs = list(raw_pubs.values())

    publications = []
    for pub in raw_pubs:
        bib = pub.get("bib") or {}
        venue = (
            bib.get("venue")
            or bib.get("journal")
            or bib.get("conference")
            or ""
        )
        arxiv_id = arxiv_id_from_text(" ".join(
            str(value)
            for value in (venue, bib.get("eprint"), pub.get("eprint_url"), pub.get("pub_url"))
            if value
        ))
        if arxiv_id:
            venue = venue or "arXiv"
        publications.append(
            {
                "id": pub.get("author_pub_id"),
                "title": bib.get("title"),
                "year": str(bib.get("pub_year") or ""),
                "citations": int(pub.get("num_citations") or 0),
                "authors": authors_from_bib(bib),
                "venue": str(venue).strip(),
                "arxiv_id": arxiv_id,
            }
        )

    cites_per_year = {
        str(year): int(count)
        for year, count in (author.get("cites_per_year") or {}).items()
    }

    return {
        "scholar_id": author.get("scholar_id"),
        "name": author.get("name"),
        "affiliation": author.get("affiliation", ""),
        "citedby": int(citedby),
        "citedby5y": int(author.get("citedby5y") or 0),
        "hindex": int(author.get("hindex") or 0),
        "hindex5y": int(author.get("hindex5y") or 0),
        "i10index": int(author.get("i10index") or 0),
        "i10index5y": int(author.get("i10index5y") or 0),
        "cites_per_year": cites_per_year,
        "publications": publications,
    }


def is_plausible(new_citedby: int, previous_citedby: int | None) -> bool:
    """Reject empty/CAPTCHA results that would clobber a known good count."""
    if new_citedby < 0:
        return False
    if previous_citedby is None:
        return True
    if new_citedby == 0 and previous_citedby > 5:
        return False
    if previous_citedby >= 20 and new_citedby < previous_citedby * 0.5:
        return False
    return True


def _parse_publications(soup: BeautifulSoup) -> list[dict[str, Any]]:
    publications = []
    for row in soup.find_all("tr", class_="gsc_a_tr"):
        title_el = row.find("a", class_="gsc_a_at")
        if title_el is None:
            continue
        href = title_el.get("href") or ""
        match = _CITATION_FOR_VIEW_RE.search(href)
        year_el = row.find("span", class_="gsc_a_h") or row.find("td", class_="gsc_a_y")
        cite_el = row.find("a", class_="gsc_a_ac") or row.find("td", class_="gsc_a_c")
        gray = row.find_all("div", class_="gs_gray")
        authors_text = gray[0].get_text(" ", strip=True) if gray else ""
        venue_text = gray[1].get_text(" ", strip=True) if len(gray) > 1 else ""
        venue, arxiv_id = parse_venue_line(venue_text)
        publications.append(
            {
                "id": match.group(1) if match else None,
                "title": title_el.get_text(strip=True),
                "year": (year_el.get_text(strip=True) if year_el else ""),
                "citations": parse_int(cite_el.get_text() if cite_el else ""),
                "authors": split_authors(authors_text),
                "venue": venue,
                "arxiv_id": arxiv_id,
            }
        )
    return publications


def _parse_cites_per_year(soup: BeautifulSoup) -> dict[str, int]:
    years = [parse_int(el.get_text()) for el in soup.find_all("span", class_="gsc_g_t")]
    if not years:
        return {}
    cites = [0] * len(years)
    for bar in soup.find_all("a", class_="gsc_g_a"):
        style = bar.get("style") or ""
        z = style.rsplit(":", 1)[-1].strip()
        try:
            index_from_right = int(z)
        except ValueError:
            continue
        label = bar.find("span", class_="gsc_g_al")
        cites[-index_from_right] = parse_int(label.get_text() if label else "")
    return {str(year): count for year, count in zip(years, cites)}


def split_authors(text: str | None) -> list[str]:
    if not text:
        return []
    parts = []
    for chunk in re.split(r",|\band\b", text):
        name = " ".join(chunk.split()).strip(" .")
        if not name:
            continue
        if name.lower() in {"et al", "et al."}:
            parts.append("et al.")
            continue
        parts.append(name)
    return parts


def authors_from_bib(bib: dict[str, Any]) -> list[str]:
    raw = bib.get("author") or bib.get("author_list")
    if isinstance(raw, list):
        return [str(name).strip() for name in raw if str(name).strip()]
    if isinstance(raw, str):
        if " and " in raw:
            return [name.strip() for name in raw.split(" and ") if name.strip()]
        return split_authors(raw)
    return []


def arxiv_id_from_text(text: str | None) -> str | None:
    if not text:
        return None
    match = _ARXIV_RE.search(text)
    return match.group(1) if match else None


def parse_venue_line(text: str | None) -> tuple[str, str | None]:
    """Return (venue, arxiv_id) from the Scholar listing's second gray line."""
    if not text:
        return "", None
    cleaned = re.sub(r",?\s*\d{4}\s*$", "", text).strip(" ,")
    arxiv_id = arxiv_id_from_text(cleaned)
    if arxiv_id:
        return "arXiv", arxiv_id
    return cleaned, None


def normalize_title(title: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", title or "")
    text = text.replace("‐", "-").replace("—", "-").replace("–", "-")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def merge_publication_metadata(
    primary: list[dict[str, Any]], extra: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    extras = {pub.get("id"): pub for pub in extra if pub.get("id")}
    merged = []
    for pub in primary:
        other = extras.get(pub.get("id")) or {}
        item = dict(pub)
        for key in ("authors", "venue", "arxiv_id"):
            if not item.get(key) and other.get(key):
                item[key] = other[key]
        merged.append(item)
    return merged
