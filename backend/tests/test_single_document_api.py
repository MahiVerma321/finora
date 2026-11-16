import importlib
import tempfile
import unittest
from unittest.mock import patch
import os

import pymupdf
from fastapi.testclient import TestClient

import test_single_document_screening as fixtures


class SingleDocumentAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        with patch.dict(os.environ, {'FINORA_DATA_DIR': cls.directory.name}):
            cls.api = importlib.import_module('app.main')
        cls.client = TestClient(cls.api.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.directory.cleanup()

    def test_upload_analysis_and_red_evidence_for_each_document(self):
        fixture = fixtures.SingleDocumentTests()
        fixture.setUp()
        try:
            for title in ('IRCTC ticket', 'Bus ticket', 'Flight boarding pass', 'Invoice', 'Letter'):
                with self.subTest(title=title):
                    path = fixture.make_document(title, 'whiteout')
                    response = self.client.post('/api/upload', files={'file': ('submitted.pdf', path.read_bytes(), 'application/pdf')})
                    self.assertEqual(response.status_code, 200)
                    file_id = response.json()['file_id']
                    response = self.client.get(f'/api/manipulation/{file_id}')
                    self.assertEqual(response.status_code, 200, response.text)
                    report = response.json()['manipulation_analysis']
                    self.assertGreater(report['visual_evidence']['content_stream_highlights'], 0)
                    asset = self.client.get(report['visual_evidence']['visualization_url'])
                    self.assertEqual(asset.status_code, 200)
                    with pymupdf.open(stream=asset.content, filetype='pdf') as doc:
                        self.assertTrue(any(d.get('color') == (1, 0, 0) for d in doc[1].get_drawings()))
                    with patch.object(self.api, 'generate_visual_evidence', side_effect=ValueError('render failure')):
                        response = self.client.get(f'/api/manipulation/{file_id}')
                    partial = response.json()['manipulation_analysis']
                    self.assertEqual(partial['status'], 'completed_with_errors')
                    self.assertEqual(partial['visual_evidence']['status'], 'unavailable')
                    self.assertTrue(partial['checks']['content_stream_analysis']['findings'])
            self.assertFalse(any('/api/compare/' in getattr(route, 'path', '') for route in self.api.app.routes))
        finally:
            fixture.tearDown()
