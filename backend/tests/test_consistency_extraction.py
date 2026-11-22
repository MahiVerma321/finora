"""Consistency extraction regressions; no network or model downloads required."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

import pymupdf
from fastapi.testclient import TestClient

from app import ocr_engine
from app.authenticity.generic_extractor import extract_generic_fields


class ConsistencyExtractionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "document.pdf"

    def make_pdf(self, pages):
        with pymupdf.open() as document:
            for text in pages:
                page = document.new_page()
                if text:
                    page.insert_text((72, 72), text)
            document.save(self.path)
        return self.path

    def test_native_pdf_never_loads_paddle_or_rasterizes(self):
        self.make_pdf(["TAX INVOICE\nInvoice Number: INV-123", "Grand Total: 1180.00"])
        with patch.object(ocr_engine, "_get_paddleocr_class", side_effect=AssertionError("Paddle loaded")):
            with patch.object(pymupdf.Page, "get_pixmap", side_effect=AssertionError("Page rasterized")):
                result = ocr_engine.extract_consistency_text(self.path)
        self.assertEqual(result["technique"], "PyMuPDF native text extraction")
        self.assertIn("INV-123", result["full_text"])
        self.assertEqual(result["line_count"], 3)
        self.assertEqual([line["page"] for line in result["lines"]], [1, 1, 2])
        self.assertTrue(all(line["confidence"] is None for line in result["lines"]))

    def test_module_import_does_not_import_paddle(self):
        program = (
            "import sys; from app import ocr_engine; "
            "assert 'paddleocr' not in sys.modules; "
            "assert 'paddle' not in sys.modules; "
            "assert 'paddlex' not in sys.modules"
        )
        completed = subprocess.run([sys.executable, "-B", "-c", program], capture_output=True, text=True, timeout=20)
        self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_native_boxes_support_separate_label_value_spatial_matching(self):
        with pymupdf.open() as document:
            page = document.new_page()
            page.insert_text((72, 72), "Invoice Number")
            page.insert_text((175, 72), "INV-123")
            document.save(self.path)
        result = ocr_engine.extract_consistency_text(self.path)
        fields = extract_generic_fields(result["lines"])["fields"]
        self.assertEqual(fields["invoice_number"]["value"], "INV-123")
        self.assertTrue(all(len(line["box"]) == 4 and len(line["box"][0]) == 2 for line in result["lines"]))

    def test_mixed_pdf_only_ocr_scanned_page_and_preserves_page_numbers(self):
        self.make_pdf(["Native first page", "", "Native third page"])
        captured_images = []

        def scan(image_path):
            captured_images.append(image_path)
            self.assertTrue(image_path.is_file())
            with pymupdf.open(image_path) as image:
                self.assertLessEqual(max(image[0].rect.width, image[0].rect.height), 1801)
            return [{"text": "Scanned second page", "confidence": 0.97, "box": None, "page": 1}]

        with patch.object(ocr_engine, "_get_paddleocr_class", return_value=Mock()):
            with patch.object(ocr_engine, "extract_from_image", side_effect=scan) as predict:
                result = ocr_engine.extract_consistency_text(self.path)
        self.assertEqual(predict.call_count, 1)
        self.assertEqual([line["page"] for line in result["lines"]], [1, 2, 3])
        self.assertIn("Scanned second page", result["full_text"])
        self.assertIn("PyMuPDF", result["technique"])
        self.assertIn("PaddleOCR", result["technique"])
        self.assertFalse(captured_images[0].exists())

    def test_scan_with_selectable_footer_still_uses_ocr(self):
        with pymupdf.open() as document:
            page = document.new_page()
            image = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 20, 20), False)
            image.clear_with(220)
            page.insert_image(pymupdf.Rect(0, 0, 595, 750), pixmap=image)
            page.insert_text((72, 800), "Scanner footer")
            document.save(self.path)
        with patch.object(ocr_engine, "_get_paddleocr_class", return_value=Mock()):
            with patch.object(ocr_engine, "extract_from_image", return_value=[{"text": "Scanned body", "page": 1}]) as predict:
                result = ocr_engine.extract_consistency_text(self.path)
        predict.assert_called_once()
        self.assertEqual(result["full_text"], "Scanned body")

    def test_oversized_pdf_raster_is_bounded_before_ocr(self):
        with pymupdf.open() as document:
            document.new_page(width=12000, height=16000)
            document.save(self.path)
        original = pymupdf.Page.get_pixmap
        dimensions = []

        def capture(page, *args, **kwargs):
            pixmap = original(page, *args, **kwargs)
            dimensions.append((pixmap.width, pixmap.height, pixmap.n))
            return pixmap

        with patch.object(ocr_engine, "_get_paddleocr_class", return_value=Mock()):
            with patch.object(pymupdf.Page, "get_pixmap", capture):
                with patch.object(ocr_engine, "extract_from_image", return_value=[{"text": "Scan", "page": 1}]):
                    ocr_engine.extract_consistency_text(self.path)
        self.assertEqual(dimensions, [(1350, 1800, 3)])

    def test_missing_paddle_for_scan_is_an_explicit_error(self):
        self.make_pdf([""])
        with patch.object(ocr_engine, "_get_paddleocr_class", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "requires PaddleOCR"):
                ocr_engine.extract_consistency_text(self.path)

    def test_empty_extraction_does_not_produce_successful_consistency_report(self):
        self.make_pdf([""])
        with patch.object(ocr_engine, "_get_paddleocr_class", return_value=Mock()):
            with patch.object(ocr_engine, "extract_from_image", return_value=[]):
                with self.assertRaisesRegex(ValueError, "No readable text"):
                    ocr_engine.extract_consistency_text(self.path)

    def test_failure_removes_rendered_page(self):
        self.make_pdf([""])
        captured_images = []

        def fail(image_path):
            captured_images.append(image_path)
            raise RuntimeError("Inference failed")

        with patch.object(ocr_engine, "_get_paddleocr_class", return_value=Mock()):
            with patch.object(ocr_engine, "extract_from_image", side_effect=fail):
                with self.assertRaisesRegex(RuntimeError, "Inference failed"):
                    ocr_engine.extract_consistency_text(self.path)
        self.assertFalse(captured_images[0].exists())

    def test_repeated_scans_reuse_engine_without_reinitializing(self):
        factory = Mock()
        ocr_engine.get_ocr_engine.cache_clear()
        self.addCleanup(ocr_engine.get_ocr_engine.cache_clear)
        with patch.object(ocr_engine, "_get_paddleocr_class", return_value=factory):
            ocr_engine.run_ocr(Path("first.png"))
            ocr_engine.run_ocr(Path("second.png"))
        factory.assert_called_once()
        self.assertEqual(factory.return_value.predict.call_count, 2)
        self.assertEqual(
            [call.args[0] for call in factory.return_value.predict.call_args_list],
            ["first.png", "second.png"],
        )


class ConsistencyAPITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        # Load a separate API instance so its temporary storage cannot leak via
        # the app.main module cache into the existing API test class.
        spec = importlib.util.spec_from_file_location(
            "consistency_test_api", Path(ocr_engine.__file__).with_name("main.py")
        )
        cls.api = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {"FINORA_DATA_DIR": cls.directory.name}):
            spec.loader.exec_module(cls.api)
        cls.client = TestClient(cls.api.app)

    @classmethod
    def tearDownClass(cls):
        cls.client.close()
        cls.directory.cleanup()

    def upload(self, text):
        with pymupdf.open() as document:
            page = document.new_page()
            if text:
                page.insert_text((72, 72), text)
            payload = document.tobytes()
        response = self.client.post("/api/upload", files={"file": ("invoice.pdf", payload, "application/pdf")})
        self.assertEqual(response.status_code, 200)
        return response.json()["file_id"]

    def test_native_invoice_completes_without_ocr_and_keeps_response_contract(self):
        file_id = self.upload(
            "Acme Global Solutions Inc.\nTAX INVOICE\nInvoice Number: INV-2026-0881\n"
            "Invoice Date: 15-Jan-2026\nPayment Due Date: 15-Feb-2026\n"
            "Subtotal: $ 1000.00\nTax Amount: $ 180.00\nGrand Total: $ 1180.00"
        )
        with patch.object(ocr_engine, "_get_paddleocr_class", side_effect=AssertionError("Paddle loaded")):
            response = self.client.get(f"/api/consistency/{file_id}")
        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["analysis_status"], "completed")
        self.assertEqual(payload["document_type"], "invoice")
        self.assertEqual(payload["overall_status"], "passed")
        self.assertEqual(payload["extracted_document"], payload["extracted_ticket"])
        self.assertIn("financial_reconciliation", [c["name"] for c in payload["consistency_report"]["checks"]])
        self.assertIn("checks", payload["field_validation_report"])

    def test_unreadable_scan_returns_extraction_error(self):
        file_id = self.upload("")
        with patch.object(ocr_engine, "_get_paddleocr_class", return_value=Mock()):
            with patch.object(ocr_engine, "extract_from_image", return_value=[]):
                response = self.client.get(f"/api/consistency/{file_id}")
        self.assertEqual(response.status_code, 422)
        self.assertIn("No readable text", response.json()["detail"])

    def test_explicit_ocr_endpoint_keeps_existing_extraction_path(self):
        file_id = self.upload("Native text")
        expected = {"technique": "PaddleOCR", "lines": [], "full_text": "", "line_count": 0}
        with patch.object(self.api, "extract_document_text", return_value=expected) as extract:
            with patch.object(self.api, "extract_consistency_text", side_effect=AssertionError("Consistency path used")):
                response = self.client.get(f"/api/ocr/{file_id}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ocr_result"], expected)
        extract.assert_called_once()

    def test_native_invoice_financial_mismatch_is_still_reported(self):
        file_id = self.upload(
            "TAX INVOICE\nInvoice Number: INV-123\nInvoice Date: 15-Jan-2026\n"
            "Subtotal: $ 1000.00\nTax Amount: $ 180.00\nGrand Total: $ 9999.00"
        )
        with patch.object(ocr_engine, "_get_paddleocr_class", side_effect=AssertionError("Paddle loaded")):
            response = self.client.get(f"/api/consistency/{file_id}")
        self.assertEqual(response.status_code, 200, response.text)
        report = response.json()["consistency_report"]
        financial = next(check for check in report["checks"] if check["name"] == "financial_reconciliation")
        self.assertEqual(financial["status"], "warning")
        self.assertEqual(response.json()["overall_status"], "incomplete")

    def test_same_filename_different_contents_produce_independent_api_results(self):
        outcomes = []
        file_ids = []
        with patch.object(ocr_engine, "_get_paddleocr_class", side_effect=AssertionError("Paddle loaded")):
            for scenario in ("valid", "wrong_total", "wrong_date"):
                reference = uuid4().hex[:12]
                subtotal = int(reference[:4], 16) + 1
                tax = 37
                total = subtotal + tax if scenario != "wrong_total" else subtotal * 10
                due_date = "20-Apr-2027" if scenario != "wrong_date" else "20-Feb-2027"
                file_id = self.upload(
                    f"Acme {reference}\nTAX INVOICE\nInvoice Number: {reference}\n"
                    f"Invoice Date: 20-Mar-2027\nPayment Due Date: {due_date}\n"
                    f"Subtotal: {subtotal}\nTax Amount: {tax}\nGrand Total: {total}"
                )
                response = self.client.get(f"/api/consistency/{file_id}")
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(result["extracted_document"]["fields"]["invoice_number"]["value"], reference)
                self.assertEqual(result["issuer"], f"Acme {reference}")
                outcomes.append(result["overall_status"])
                file_ids.append(file_id)
        self.assertEqual(outcomes, ["passed", "incomplete", "review_required"])
        self.assertEqual(len(set(file_ids)), 3)


if __name__ == "__main__":
    unittest.main()
