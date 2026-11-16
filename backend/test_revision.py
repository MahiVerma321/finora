import unittest
from pathlib import Path

FIXTURE_PDF = Path("test_fixtures/sample.pdf")


class TestRevision(unittest.TestCase):
    def test_revision_markers_returns_expected_keys(self):
        """inspect_revision_markers should return marker analysis structure."""
        try:
            from app.revision_detector import inspect_revision_markers
        except ImportError as err:
            self.skipTest(f"Dependencies not installed: {err}")

        if not FIXTURE_PDF.exists():
            self.skipTest(
                f"Fixture PDF not found: {FIXTURE_PDF}. "
                "Place a test PDF at that path to enable this test."
            )

        result = inspect_revision_markers(FIXTURE_PDF)
        self.assertIsInstance(result, dict)
        self.assertIn("startxref_marker_count", result)
        self.assertIn("eof_marker_count", result)
        self.assertIn("is_linearized", result)

    def test_prev_chain_returns_expected_keys(self):
        """analyze_prev_chain should return cross-reference chain structure."""
        try:
            from app.revision_detector import analyze_prev_chain
        except ImportError as err:
            self.skipTest(f"Dependencies not installed: {err}")

        if not FIXTURE_PDF.exists():
            self.skipTest(
                f"Fixture PDF not found: {FIXTURE_PDF}. "
                "Place a test PDF at that path to enable this test."
            )

        result = analyze_prev_chain(FIXTURE_PDF)
        self.assertIsInstance(result, dict)
        self.assertIn("xref_section_count", result)
        self.assertIn("revision_chain", result)


if __name__ == "__main__":
    unittest.main()
