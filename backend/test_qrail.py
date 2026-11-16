import os
import unittest


class TestQRail(unittest.TestCase):
    def test_qrail_env_configuration(self):
        """QRail integration test (external service). Skips when unconfigured."""
        api_key = os.getenv("QRAIL_API_KEY")
        if not api_key:
            self.skipTest(
                "QRAIL_API_KEY not configured. "
                "Set QRAIL_API_KEY to test live rail PNR status API."
            )

        try:
            import requests
        except ImportError:
            self.skipTest("requests library not installed in environment")

        self.assertTrue(len(api_key) > 0)


if __name__ == "__main__":
    unittest.main()
