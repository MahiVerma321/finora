import unittest
from pathlib import Path

FIXTURE_PDF = Path("test_fixtures/sample.pdf")


class TestProvenance(unittest.TestCase):
    def test_provenance_structure(self):
        """analyze_provenance should return structured provenance checks."""
        try:
            from app.provenance_detector import analyze_provenance
        except ImportError as err:
            self.skipTest(f"Dependencies not installed: {err}")

        if not FIXTURE_PDF.exists():
            self.skipTest(
                f"Fixture PDF not found: {FIXTURE_PDF}. "
                "Place a test PDF at that path to enable this test."
            )

        result = analyze_provenance(FIXTURE_PDF)
        self.assertIsInstance(result, dict)
        self.assertIn("manifest_detected", result)


if __name__ == "__main__":
    unittest.main()
