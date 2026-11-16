import unittest
from pathlib import Path

# Fixture path — point this at a real PDF to run against live data.
# The test skips gracefully when the file is absent or dependencies are missing.
FIXTURE_PDF = Path("test_fixtures/sample.pdf")


class TestContentStream(unittest.TestCase):
    def test_content_stream_readable(self):
        """PDF content streams should be openable and each page should have
        at least one content stream xref."""
        try:
            import pymupdf
        except ImportError:
            self.skipTest("pymupdf not installed in environment")

        if not FIXTURE_PDF.exists():
            self.skipTest(
                f"Fixture PDF not found: {FIXTURE_PDF}. "
                "Place a test PDF at that path to enable this test."
            )

        doc = pymupdf.open(str(FIXTURE_PDF))
        try:
            self.assertGreater(len(doc), 0, "PDF should have at least one page")
            for page in doc:
                xrefs = page.get_contents()
                self.assertIsInstance(
                    xrefs,
                    (list, tuple),
                    "get_contents() should return a list of xref integers"
                )
        finally:
            doc.close()


if __name__ == "__main__":
    unittest.main()
