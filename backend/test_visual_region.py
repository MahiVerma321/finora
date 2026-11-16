import unittest
from pathlib import Path

FIXTURE_PDF = Path("test_fixtures/sample.pdf")


class TestVisualRegion(unittest.TestCase):
    def test_visual_regions_returns_expected_keys(self):
        """analyze_visual_regions should return a dict with documented keys."""
        try:
            from app.visual_region_detector import analyze_visual_regions
        except ImportError as err:
            self.skipTest(f"Dependencies not installed: {err}")

        if not FIXTURE_PDF.exists():
            self.skipTest(
                f"Fixture PDF not found: {FIXTURE_PDF}. "
                "Place a test PDF at that path to enable this test."
            )

        result = analyze_visual_regions(FIXTURE_PDF)
        self.assertIsInstance(result, dict)
        self.assertIn("technique", result)
        self.assertIn("page_count", result)
        self.assertIn("pages", result)
        for page in result["pages"]:
            self.assertIn("page_number", page)
            self.assertIn("anomalies", page)


if __name__ == "__main__":
    unittest.main()
