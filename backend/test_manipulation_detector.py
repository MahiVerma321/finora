import unittest
from pathlib import Path

FIXTURE_PDF = Path("test_fixtures/sample.pdf")
OUTPUT_DIR = Path("test_manipulation_output")


class TestManipulationDetector(unittest.TestCase):
    def test_manipulation_detector_returns_expected_keys(self):
        """analyze_manipulation should return a dict with top-level keys."""
        try:
            from app.manipulation_detector import analyze_manipulation
        except ImportError as err:
            self.skipTest(f"Dependencies not installed: {err}")

        if not FIXTURE_PDF.exists():
            self.skipTest(
                f"Fixture PDF not found: {FIXTURE_PDF}. "
                "Place a test PDF at that path to enable this test."
            )

        result = analyze_manipulation(FIXTURE_PDF, OUTPUT_DIR)
        self.assertIsInstance(result, dict)
        self.assertTrue(
            "checks" in result or "findings" in result or "status" in result,
            "Result should contain 'checks', 'findings', or 'status'"
        )


if __name__ == "__main__":
    unittest.main()
