import json
import re
import unittest
from pathlib import Path

from parse import author_from_scholarly, is_plausible, parse_author_profile, parse_int

FIXTURE = Path(__file__).parent / "testdata" / "author_profile.html"


class ParseIntTests(unittest.TestCase):
    def test_commas_and_blank(self):
        self.assertEqual(parse_int("1,234"), 1234)
        self.assertEqual(parse_int(" 160 "), 160)
        self.assertEqual(parse_int("\xa0"), 0)
        self.assertEqual(parse_int(""), 0)
        self.assertEqual(parse_int(None), 0)


class ProfileParseTests(unittest.TestCase):
    def test_fixture_profile(self):
        html = FIXTURE.read_text(encoding="utf-8")
        author = parse_author_profile(html, "4_KIgHkAAAAJ")
        self.assertEqual(author["name"], "Changran Xu")
        self.assertEqual(author["citedby"], 160)
        self.assertEqual(author["hindex"], 6)
        self.assertEqual(author["i10index"], 6)
        self.assertEqual(author["cites_per_year"], {"2024": 7, "2025": 64, "2026": 89})
        self.assertEqual(len(author["publications"]), 3)
        self.assertEqual(author["publications"][0]["citations"], 36)
        self.assertEqual(author["publications"][1]["citations"], 1234)
        self.assertEqual(author["publications"][2]["citations"], 0)
        self.assertEqual(
            author["publications"][0]["id"], "4_KIgHkAAAAJ:W7OEmFMy1HYC"
        )

    def test_captcha_page_is_rejected(self):
        html = '<html><div id="gs_captcha_ccl">not a robot</div></html>'
        with self.assertRaises(ValueError):
            parse_author_profile(html, "4_KIgHkAAAAJ")

    def test_empty_page_is_rejected(self):
        with self.assertRaises(ValueError):
            parse_author_profile("<html><body>blocked</body></html>", "x")


class ScholarlyNormalizeTests(unittest.TestCase):
    def test_list_and_dict_publications(self):
        raw = {
            "scholar_id": "4_KIgHkAAAAJ",
            "name": "Changran Xu",
            "citedby": 160,
            "citedby5y": 160,
            "hindex": 6,
            "hindex5y": 6,
            "i10index": 6,
            "i10index5y": 6,
            "cites_per_year": {2024: 7, 2025: 64},
            "publications": [
                {
                    "author_pub_id": "abc",
                    "bib": {"title": "Paper", "pub_year": "2025"},
                    "num_citations": 36,
                }
            ],
        }
        author = author_from_scholarly(raw)
        self.assertEqual(author["citedby"], 160)
        self.assertEqual(author["cites_per_year"]["2024"], 7)
        self.assertEqual(author["publications"][0]["citations"], 36)

        raw["publications"] = {"abc": raw["publications"][0]}
        author = author_from_scholarly(raw)
        self.assertEqual(len(author["publications"]), 1)

    def test_missing_citedby(self):
        with self.assertRaises(ValueError):
            author_from_scholarly({"name": "x"})


class PlausibleTests(unittest.TestCase):
    def test_allows_small_scholar_recalculation(self):
        self.assertTrue(is_plausible(154, 158))
        self.assertTrue(is_plausible(160, None))

    def test_rejects_empty_or_halved_counts(self):
        self.assertFalse(is_plausible(0, 160))
        self.assertFalse(is_plausible(10, 160))
        self.assertFalse(is_plausible(-1, None))


class CurrentSiteDataTests(unittest.TestCase):
    def test_stored_totals_match_per_paper_sum(self):
        path = Path(__file__).resolve().parent.parent / "assets" / "results" / "gs_data.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        pubs = data["publications"]
        if isinstance(pubs, dict):
            cites = [p.get("num_citations") or p.get("citations") or 0 for p in pubs.values()]
        else:
            cites = [p.get("citations") or 0 for p in pubs]
        self.assertEqual(data["citedby"], sum(cites))
        self.assertEqual(data["scholar_id"], "4_KIgHkAAAAJ")

    def test_jekyll_data_has_by_id(self):
        path = Path(__file__).resolve().parent.parent / "_data" / "google_scholar.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(data["by_id"])
        for pub in data["publications"]:
            self.assertEqual(data["by_id"][pub["id"]]["citations"], pub["citations"])

    def test_front_matter_scholar_ids_exist_in_cache(self):
        root = Path(__file__).resolve().parent.parent
        cache = json.loads((root / "_data" / "google_scholar.json").read_text(encoding="utf-8"))
        known = {pub["id"] for pub in cache["publications"]}
        id_re = re.compile(r"^scholar_pub_id:\s*[\"']?([A-Za-z0-9_-]+:[A-Za-z0-9_-]+)[\"']?\s*$", re.M)
        mapped = []
        for path in (root / "_publications").rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            match = id_re.search(text)
            if match:
                mapped.append((path.name, match.group(1)))
                self.assertIn(match.group(1), known, msg=path.name)
        self.assertGreaterEqual(len(mapped), 7)


if __name__ == "__main__":
    unittest.main()
