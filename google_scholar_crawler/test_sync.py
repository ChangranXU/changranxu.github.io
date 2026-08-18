import tempfile
import unittest
from pathlib import Path

from parse import merge_publication_metadata, normalize_title
from sync_publications import (
    insert_scholar_pub_id,
    render_generated_markdown,
    slugify,
    sync_publications,
)


class NormalizeTitleTests(unittest.TestCase):
    def test_strips_html_and_punctuation(self):
        self.assertEqual(
            normalize_title("<strong>DeepRTL: Bridging Verilog!</strong>"),
            "deeprtl bridging verilog",
        )


class MergeMetadataTests(unittest.TestCase):
    def test_fills_missing_authors_and_venue(self):
        primary = [{"id": "a", "title": "T", "authors": [], "venue": ""}]
        extra = [{"id": "a", "authors": ["Ada"], "venue": "ICLR", "arxiv_id": None}]
        merged = merge_publication_metadata(primary, extra)
        self.assertEqual(merged[0]["authors"], ["Ada"])
        self.assertEqual(merged[0]["venue"], "ICLR")


class SyncPublicationsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        curated = self.root / "2025" / "deeprtl.md"
        curated.parent.mkdir(parents=True)
        curated.write_text(
            """---
title:          "<strong>DeepRTL: Bridging Verilog Understanding and Generation with a Unified Representation Model</strong>"
date:           2025-02-20 00:01:00 +0800
selected:       true
pub:            "ICLR"
pub_date:       "2025"
authors:
  - Yi Liu
  - Changran Xu
links:
  Code: https://github.com/PeterLau61/DeepRTL
---
""",
            encoding="utf-8",
        )
        self.curated = curated

    def tearDown(self):
        self.tmp.cleanup()

    def test_creates_new_page_and_links_existing_title(self):
        author = {
            "scholar_id": "4_KIgHkAAAAJ",
            "publications": [
                {
                    "id": "4_KIgHkAAAAJ:UeHWp8X0CEIC",
                    "title": "DeepRTL: Bridging Verilog Understanding and Generation with a Unified Representation Model",
                    "year": "2025",
                    "citations": 36,
                    "authors": ["Yi Liu"],
                    "venue": "ICLR",
                },
                {
                    "id": "4_KIgHkAAAAJ:WF5omc3nYNoC",
                    "title": "CktEvo: Repository-Level RTL Code Benchmark for Design Evolution",
                    "year": "2026",
                    "citations": 3,
                    "authors": ["Ada Lovelace", "Changran Xu"],
                    "venue": "arXiv",
                    "arxiv_id": "2601.12345",
                },
            ],
        }
        summary = sync_publications(self.root, author)
        self.assertEqual(len(summary["created"]), 1)
        self.assertEqual(summary["linked"], ["2025/deeprtl.md"])
        text = self.curated.read_text(encoding="utf-8")
        self.assertIn('scholar_pub_id: "4_KIgHkAAAAJ:UeHWp8X0CEIC"', text)
        self.assertIn("Yi Liu", text)
        self.assertIn("https://github.com/PeterLau61/DeepRTL", text)

        created = self.root / summary["created"][0]
        generated = created.read_text(encoding="utf-8")
        self.assertIn("generated:      true", generated)
        self.assertIn("Ada Lovelace", generated)
        self.assertIn("arXiv", generated)
        self.assertIn("10.48550/arXiv.2601.12345", generated)
        self.assertIn("<strong>CktEvo:", generated)

    def test_does_not_overwrite_curated_page_on_second_sync(self):
        author = {
            "scholar_id": "4_KIgHkAAAAJ",
            "publications": [
                {
                    "id": "4_KIgHkAAAAJ:UeHWp8X0CEIC",
                    "title": "DeepRTL: Bridging Verilog Understanding and Generation with a Unified Representation Model",
                    "year": "2025",
                    "citations": 36,
                }
            ],
        }
        sync_publications(self.root, author)
        before = self.curated.read_text(encoding="utf-8")
        summary = sync_publications(self.root, author)
        self.assertEqual(summary["linked"], [])
        self.assertEqual(summary["created"], [])
        self.assertEqual(self.curated.read_text(encoding="utf-8"), before)

    def test_updates_generated_pages(self):
        paper = {
            "id": "x:abc",
            "title": "Hello World",
            "year": "2026",
            "authors": ["A"],
            "venue": "ICLR",
        }
        first = sync_publications(self.root, {"scholar_id": "x", "publications": [paper]})
        paper["authors"] = ["A", "B"]
        paper["venue"] = "NeurIPS"
        second = sync_publications(self.root, {"scholar_id": "x", "publications": [paper]})
        self.assertEqual(second["updated"], first["created"])
        text = (self.root / second["updated"][0]).read_text(encoding="utf-8")
        self.assertIn("NeurIPS", text)
        self.assertIn("- B", text)

    def test_does_not_recreate_when_scholar_id_already_on_another_title(self):
        combined = self.root / "2026" / "kernel.md"
        combined.parent.mkdir(parents=True, exist_ok=True)
        combined.write_text(
            """---
title:          "<strong>From Craft to Kernel</strong>"
date:           2026-04-20 00:01:00 +0800
selected:       true
pub:            "arXiv"
pub_date:       "2026"
scholar_pub_id: "4_KIgHkAAAAJ:eQOLeE2rZwMC"
authors:
  - Xiangyu Wen
---
""",
            encoding="utf-8",
        )
        summary = sync_publications(
            self.root,
            {
                "scholar_id": "4_KIgHkAAAAJ",
                "publications": [
                    {
                        "id": "4_KIgHkAAAAJ:eQOLeE2rZwMC",
                        "title": "From Craft to Constitution: A Governance-First Paradigm for Principled Agent Engineering",
                        "year": "2025",
                        "citations": 2,
                    }
                ],
            },
        )
        self.assertEqual(summary["created"], [])
        self.assertFalse(any("constitution" in name for name in summary["created"]))

    def test_generated_date_stays_in_same_year(self):
        md = render_generated_markdown(
            {"id": "a:b", "title": "Hello", "year": "2026", "authors": []},
        )
        self.assertIn("2026-01-15 00:01:00 +0800", md)
        self.assertIn('pub_date:       "2026"', md)
        self.assertEqual(slugify("DeepRTL: Bridging Verilog"), "deeprtl-bridging-verilog")

    def test_insert_is_noop_when_id_exists(self):
        text = self.curated.read_text(encoding="utf-8")
        text = text.replace("pub_date:       \"2025\"\n", 'pub_date:       "2025"\nscholar_pub_id: "already"\n')
        self.curated.write_text(text, encoding="utf-8")
        self.assertFalse(insert_scholar_pub_id(self.curated, text, "other"))

    def test_render_escapes_title(self):
        md = render_generated_markdown(
            {"id": "a:b", "title": 'Foo "Bar"', "year": "2025", "authors": []},
        )
        self.assertIn("&quot;", md)


if __name__ == "__main__":
    unittest.main()
