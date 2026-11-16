import unittest
from pathlib import Path

FIXTURE_PDF = Path("test_fixtures/sample.pdf")


class TestPdfStructure(unittest.TestCase):
    def test_pdf_structure_returns_expected_keys(self):
        """analyze_pdf_structure should return a dict with documented keys."""
        try:
            from app.pdf_structure_detector import analyze_pdf_structure
        except ImportError as err:
            self.skipTest(f"Dependencies not installed: {err}")

        if not FIXTURE_PDF.exists():
            self.skipTest(
                f"Fixture PDF not found: {FIXTURE_PDF}. "
                "Place a test PDF at that path to enable this test."
            )

        result = analyze_pdf_structure(FIXTURE_PDF)
        self.assertIsInstance(result, dict)
        self.assertIn("technique", result)
        self.assertIn("page_count", result)
        self.assertIn("is_encrypted", result)
        self.assertIn("trailer_analysis", result)
        self.assertIn("object_analysis", result)
        self.assertIn("page_analysis", result)
        self.assertIn("signature_analysis", result)
        self.assertIn("annotation_object_analysis", result)


if __name__ == "__main__":
    unittest.main()
