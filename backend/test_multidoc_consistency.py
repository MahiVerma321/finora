import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import unittest

from app.authenticity.ticket_schema import make_document_record
from app.authenticity.ticket_extractor import extract_document
from app.authenticity.consistency_detector import analyze_consistency


class TestMultiDocConsistency(unittest.TestCase):
    def test_invoice_extraction_and_consistency(self):
        """Test commercial invoice extraction and financial reconciliation check."""
        invoice_ocr = {
            "lines": [
                {"text": "Acme Global Solutions Inc.", "confidence": 0.99, "page": 1, "box": None},
                {"text": "TAX INVOICE", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Invoice Number: INV-2026-0881", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Invoice Date: 15-Jan-2026", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Payment Due Date: 15-Feb-2026", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Billed To: Globex Corporation", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Subtotal: $ 1000.00", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Tax Amount: $ 180.00", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Grand Total: $ 1180.00", "confidence": 0.99, "page": 1, "box": None},
            ]
        }

        doc = extract_document(invoice_ocr)
        self.assertEqual(doc["document_type"], "invoice")
        self.assertEqual(doc["document_category"], "commercial")
        self.assertIn("INV-2026-0881", doc["fields"]["invoice_number"]["value"])
        self.assertIn("15-Jan-2026", doc["fields"]["invoice_date"]["value"])

        report = analyze_consistency(doc)
        self.assertEqual(report["status"], "passed")
        check_names = [c["name"] for c in report["checks"]]
        self.assertIn("required_fields", check_names)
        self.assertIn("payment_due_date", check_names)
        self.assertIn("financial_reconciliation", check_names)

        # Route check must NOT be run on invoices
        self.assertNotIn("route_check", check_names)

    def test_invoice_financial_discrepancy_flagged(self):
        """Test invoice where subtotal + tax != total amount."""
        bad_invoice = make_document_record(
            document_type="invoice",
            issuer="Test Corp",
            fields={
                "invoice_number": "INV-001",
                "invoice_date": "2026-01-01",
                "due_date": "2026-01-30",
                "subtotal": "500.00",
                "tax_amount": "50.00",
                "total_amount": "999.00",  # Inconsistent: 500 + 50 != 999
            }
        )
        report = analyze_consistency(bad_invoice)
        reconcile_check = next(
            c for c in report["checks"] if c["name"] == "financial_reconciliation"
        )
        self.assertEqual(reconcile_check["status"], "warning")

    def test_invoice_due_date_preceding_invoice_date_flagged(self):
        """Test invoice where due date is before invoice date."""
        bad_dates_invoice = make_document_record(
            document_type="invoice",
            issuer="Test Corp",
            fields={
                "invoice_number": "INV-002",
                "invoice_date": "2026-02-15",
                "due_date": "2026-01-15",  # Invalid: due date before invoice date
                "total_amount": "100.00",
            }
        )
        report = analyze_consistency(bad_dates_invoice)
        date_check = next(
            c for c in report["checks"] if c["name"] == "payment_due_date"
        )
        self.assertEqual(date_check["status"], "failed")

    def test_international_airline_not_hardcoded_to_indigo(self):
        """Test flight extraction with United Airlines."""
        flight_ocr = {
            "lines": [
                {"text": "United Airlines", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Boarding Pass", "confidence": 0.99, "page": 1, "box": None},
                {"text": "UA 890", "confidence": 0.99, "page": 1, "box": None},
                {"text": "SAN FRANCISCO (SFO) To NEW YORK (JFK)", "confidence": 0.99, "page": 1, "box": None},
                {"text": "20 Nov 2026", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Boarding Time: 08:30", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Departure Time: 09:15", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Seat: 14B", "confidence": 0.99, "page": 1, "box": None},
            ]
        }
        doc = extract_document(flight_ocr)
        self.assertEqual(doc["document_type"], "flight")
        self.assertEqual(doc["issuer"], "United Airlines")
        self.assertNotEqual(doc["issuer"], "IndiGo")

        report = analyze_consistency(doc)
        self.assertEqual(report["status"], "passed")

    def test_international_railway_not_hardcoded_to_irctc(self):
        """Test train extraction with Amtrak."""
        amtrak_ocr = {
            "lines": [
                {"text": "Amtrak National Railroad", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Train No: 2150", "confidence": 0.99, "page": 1, "box": None},
                {"text": "From: Washington Union Station", "confidence": 0.99, "page": 1, "box": None},
                {"text": "To: Boston South Station", "confidence": 0.99, "page": 1, "box": None},
                {"text": "Journey Date: 12-Dec-2026", "confidence": 0.99, "page": 1, "box": None},
            ]
        }
        doc = extract_document(amtrak_ocr)
        self.assertEqual(doc["document_type"], "train")
        self.assertEqual(doc["issuer"], "Amtrak")
        self.assertNotEqual(doc["issuer"], "IRCTC")

    def test_generic_document_does_not_crash_or_fail_with_unsupported_type(self):
        """Generic documents should be handled gracefully without 'unsupported type' failure."""
        generic_doc = make_document_record(
            document_type="generic",
            issuer="Generic Corp",
            fields={
                "document_date": "2026-05-10",
                "reference_number": "REF-9988",
            }
        )
        report = analyze_consistency(generic_doc)
        # Should not fail with 'unsupported ticket type'
        self.assertIn(report["status"], ["passed", "incomplete"])
        check_names = [c["name"] for c in report["checks"]]
        self.assertIn("document_structure", check_names)
        self.assertNotIn("route_check", check_names)


if __name__ == "__main__":
    unittest.main()
