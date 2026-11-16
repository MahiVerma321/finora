import unittest
from pathlib import Path

FIXTURE_PDF = Path("test_fixtures/sample.pdf")


class TestAiDetector(unittest.TestCase):
    def test_ai_detector_structure(self):
        """analyze_ai_file should return a valid analysis structure."""
        try:
            from app.ai_detector import analyze_ai_file
        except ImportError as err:
            self.skipTest(f"Dependencies not installed: {err}")

        if not FIXTURE_PDF.exists():
            self.skipTest(
                f"Fixture PDF not found: {FIXTURE_PDF}. "
                "Place a test PDF at that path to enable this test."
            )

        result = analyze_ai_file(FIXTURE_PDF)
        self.assertIsInstance(result, dict)
        self.assertIn("status", result)


if __name__ == "__main__":
    unittest.main()
