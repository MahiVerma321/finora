"""
Pytest configuration for FINORA backend test suite.

To run tests against live document samples, place sample PDFs in:
    backend/test_fixtures/sample.pdf
or set the FIXTURE_PDF environment variable.

Tests will skip gracefully when fixtures are not present.
"""
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "test_fixtures"
FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
