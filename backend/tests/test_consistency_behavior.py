"""Check that consistency decisions follow document evidence, not fixed values."""
import unittest
from uuid import uuid4

from app.authenticity.consistency_detector import analyze_consistency, parse_numeric_amount
from app.authenticity.observation_collector import collect_repeated_observations
from app.authenticity.ticket_extractor import detect_issuer, extract_document
from app.authenticity.ticket_schema import make_document_record


def text_lines(text):
    return [
        {"text": value, "confidence": None, "page": index + 1, "box": None}
        for index, value in enumerate(text.splitlines())
    ]


class EvidenceDrivenConsistencyTests(unittest.TestCase):
    def test_distinct_documents_keep_their_own_values_and_results(self):
        records = []
        for index, (subtotal, tax, total) in enumerate(((417, 31, 448), (863, 47, 9999))):
            reference = uuid4().hex[:12]
            vendor = f"Supplier {reference}"
            doc = extract_document({"lines": text_lines(
                f"{vendor}\nTAX INVOICE\nInvoice Number: {reference}\n"
                f"Invoice Date: 17-Mar-2027\nSubtotal: {subtotal}\n"
                f"Tax Amount: {tax}\nGrand Total: {total}"
            )})
            self.assertEqual(doc["issuer"], vendor)
            self.assertEqual(doc["fields"]["invoice_number"]["value"], reference)
            self.assertEqual(float(doc["fields"]["total_amount"]["value"]), total)
            report = analyze_consistency(doc)
            financial = next(c for c in report["checks"] if c["name"] == "financial_reconciliation")
            self.assertEqual(financial["status"], "passed" if index == 0 else "warning")
            records.append(doc)
        self.assertNotEqual(records[0]["issuer"], records[1]["issuer"])
        self.assertNotEqual(records[0]["fields"], records[1]["fields"])

    def test_classification_is_driven_by_content(self):
        for content, expected in (
            ("Boarding Pass", "flight"),
            ("Train Number: 5197\nJourney Date: 21-Mar-2027", "train"),
            ("Bus Ticket", "bus"),
            ("TAX INVOICE", "invoice"),
            ("Payment Receipt", "receipt"),
            ("Bank Statement", "bank_statement"),
            ("Certificate of Completion", "certificate"),
            ("Ordinary project meeting notes", "generic"),
        ):
            with self.subTest(expected=expected):
                doc = extract_document({"lines": text_lines(content)})
                self.assertEqual(doc["document_type"], expected)

    def test_unknown_issuers_are_not_fabricated(self):
        for kind in ("flight", "train", "bus", "invoice", "receipt", "bank_statement", "certificate", "generic"):
            with self.subTest(kind=kind):
                self.assertIsNone(detect_issuer("", kind))
        self.assertIsNone(detect_issuer("Electronic Reservation Slip\nPassengers", "train"))

    def test_known_issuers_require_matching_text(self):
        for name, kind in (("Delta", "flight"), ("Amtrak", "train"), ("FlixBus", "bus")):
            with self.subTest(name=name):
                self.assertEqual(detect_issuer(name, kind), name)
                self.assertIsNone(detect_issuer("No provider identified", kind))

    def test_labelled_issuer_supports_unlisted_providers(self):
        provider = "Carrier " + uuid4().hex[:10]
        doc = extract_document({"lines": text_lines(f"Boarding Pass\nAirline: {provider}")})
        self.assertEqual(doc["issuer"], provider)
        self.assertEqual(doc["fields"]["issuer"]["source_text"], f"Airline: {provider}")

    def test_missing_issuer_is_reported_as_missing(self):
        doc = extract_document({"lines": text_lines(
            "TAX INVOICE\nInvoice Number: XYZ-531\nInvoice Date: 17-Mar-2027\nGrand Total: 42.00"
        )})
        self.assertIsNone(doc["issuer"])
        report = analyze_consistency(doc)
        required = next(c for c in report["checks"] if c["name"] == "required_fields")
        self.assertIn("issuer", required["message"])
        self.assertEqual(report["overall_status"], "incomplete")

    def test_repeated_field_check_can_pass_or_warn(self):
        first = uuid4().hex[:12]
        for second, expected in ((first, "passed"), (uuid4().hex[:12], "warning")):
            with self.subTest(expected=expected):
                doc = extract_document({"lines": text_lines(
                    f"TAX INVOICE\nInvoice Number: {first}\nInvoice Number: {second}"
                )})
                values = doc["observations"]["repeated_fields"]["invoice_number"]
                self.assertEqual([v["value"] for v in values], [first, second])
                report = analyze_consistency(doc)
                check = next(c for c in report["checks"] if c["name"] == "repeated_invoice_number")
                self.assertEqual(check["status"], expected)

    def test_separate_label_value_lines_detect_conflicting_seats(self):
        lines = [
            {"text": value, "page": 1, "box": None}
            for value in ("Seat Number", "17A", "Seat Number", "28B")
        ]
        collected = collect_repeated_observations(lines, {"seat": {"value": "17A"}})
        self.assertEqual(
            [v["value"] for v in collected["repeated_observations"]["seat"]],
            ["17A", "28B"],
        )

    def test_short_identifiers_do_not_match_different_longer_identifiers(self):
        lines = text_lines("INV-12\nReference INV-123")
        collected = collect_repeated_observations(lines, {"invoice_number": {"value": "INV-12"}})
        self.assertNotIn("invoice_number", collected["repeated_observations"])

    def test_total_tax_is_not_a_repeat_of_total(self):
        collected = collect_repeated_observations(
            text_lines("Grand Total: 480\nTotal Tax: 80"),
            {"total_amount": {"value": "480"}},
        )
        self.assertNotIn("total_amount", collected["repeated_observations"])

    def test_date_and_route_changes_change_decisions(self):
        for origin, destination, due_date, expected in (
            ("Oxford", "Bath", "2027-04-20", "passed"),
            ("Oxford", "Oxford", "2027-04-20", "review_required"),
            ("Oxford", "Bath", "2027-02-20", "review_required"),
        ):
            with self.subTest(destination=destination, due_date=due_date):
                doc = make_document_record("invoice", "Example Co", {
                    "invoice_number": "INV-581", "invoice_date": "2027-03-20",
                    "due_date": due_date, "total_amount": "120",
                    "origin": origin, "destination": destination,
                })
                self.assertEqual(analyze_consistency(doc)["overall_status"], expected)

    def test_failed_field_validation_affects_combined_status(self):
        for seat, expected in (("17A", "passed"), ("invalid seat value!", "review_required")):
            with self.subTest(seat=seat):
                doc = make_document_record("flight", "Example Air", {
                    "origin": "Oxford", "destination": "Bath", "seat": seat,
                    "boarding_time": "08:30", "departure_time": "09:00",
                })
                self.assertEqual(analyze_consistency(doc)["overall_status"], expected)

    def test_zero_amount_is_valid_input_not_missing(self):
        self.assertEqual(parse_numeric_amount(0), 0.0)
        doc = make_document_record("invoice", "Example Co", {
            "invoice_number": "INV-000", "invoice_date": "2027-03-20",
            "subtotal": 0, "tax_amount": 0, "total_amount": 0,
        })
        check = next(c for c in analyze_consistency(doc)["checks"] if c["name"] == "financial_reconciliation")
        self.assertEqual(check["status"], "passed")


if __name__ == "__main__":
    unittest.main()
