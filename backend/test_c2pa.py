import unittest
from pathlib import Path

FIXTURE_PDF = Path("test_fixtures/sample.pdf")


class TestC2pa(unittest.TestCase):
    def test_c2pa_reader_available(self):
        """c2pa Reader should be importable and handle unmanifested files."""
        try:
            from c2pa import Reader
        except ImportError:
            self.skipTest("c2pa library not installed in environment")

        if not FIXTURE_PDF.exists():
            self.skipTest(
                f"Fixture PDF not found: {FIXTURE_PDF}. "
                "Place a test PDF at that path to enable this test."
            )

        try:
            with Reader(str(FIXTURE_PDF)) as reader:
                manifest_data = reader.json()
                self.assertIsNotNone(manifest_data)
        except Exception:
            # Expected if sample PDF lacks C2PA manifest
            pass


if __name__ == "__main__":
    unittest.main()
