import unittest
from pathlib import Path

FIXTURE_PDF = Path("test_fixtures/sample.pdf")


class TestPdfGeneration(unittest.TestCase):
    def test_pdf_generation_returns_expected_keys(self):
        """analyze_pdf_generation should return a dict with documented keys."""
        try:
            from app.pdf_generation_detector import analyze_pdf_generation
        except ImportError as err:
            self.skipTest(f"Dependencies not installed: {err}")

        if not FIXTURE_PDF.exists():
            self.skipTest(
                f"Fixture PDF not found: {FIXTURE_PDF}. "
                "Place a test PDF at that path to enable this test."
            )

        result = analyze_pdf_generation(FIXTURE_PDF)
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)
        self.assertIn("analysis_type", result)
        if result["status"] == "completed":
            self.assertIn("checks", result)
            self.assertIn("findings", result)
            self.assertIn("assessment", result)


if __name__ == "__main__":
    unittest.main()
