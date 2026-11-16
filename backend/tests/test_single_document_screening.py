import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pikepdf
import pymupdf

from app.content_stream_detector import analyze_content_streams
from app.manipulation_detector import analyze_manipulation
from app.visual_evidence import generate_visual_evidence


class SingleDocumentTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)

    def tearDown(self):
        self.directory.cleanup()

    def make_document(self, title, edit=None, rotation=0, crop=False):
        path = self.root / "submitted.pdf"
        with pymupdf.open() as doc:
            doc.new_page().insert_text((72, 72), "Cover page")
            page = doc.new_page()
            page.insert_text((72, 72), title)
            if edit == "background":
                page.draw_rect(pymupdf.Rect(70, 85, 145, 105), fill=(1, 1, 1))
            page.insert_text((72, 100), "shivam", fontname="helv")
            if edit in ("whiteout", "removed", "translucent"):
                page.draw_rect(pymupdf.Rect(70, 85, 145, 105), fill=(1, 1, 1),
                               fill_opacity=0.3 if edit == "translucent" else 1, color=None)
                if edit == "whiteout":
                    page.insert_text((72, 100), "sivam", fontname="cour")
            if edit == "empty":
                doc.update_stream(page.get_contents()[-1], b"BT /helv 11 Tf 1 0 0 1 72 742 Tm ET")
                page.insert_text((72, 100), "sivam", fontname="cour")
            if crop:
                page.set_cropbox(pymupdf.Rect(30, 40, 550, 800))
            page.set_rotation(rotation)
            doc.save(path)
        return path

    def test_train_bus_flight_invoice_and_letter(self):
        for title in ("IRCTC electronic reservation slip", "Bus ticket", "Flight boarding pass", "Tax invoice", "Employment letter"):
            for edit in ("whiteout", "empty", "removed"):
                with self.subTest(title=title, edit=edit):
                    path = self.make_document(title, edit)
                    findings = analyze_content_streams(path)["findings"]
                    self.assertTrue(findings)
                    self.assertTrue(all(f["page"] == 2 for f in findings))
                    evidence = self.root / "highlighted.pdf"
                    result = generate_visual_evidence(path, findings, evidence)
                    self.assertGreater(result["highlighted_regions"], 0)
                    with pymupdf.open(evidence) as doc:
                        red = [drawing for drawing in doc[1].get_drawings() if drawing.get("color") == (1, 0, 0)]
                        self.assertTrue(red)
                        self.assertFalse(any(d.get("color") == (1, 0, 0) for d in doc[0].get_drawings()))

    def test_unchanged_background_and_translucent_highlight(self):
        for edit in (None, "background", "translucent"):
            path = self.make_document("Invoice", edit)
            self.assertEqual(analyze_content_streams(path)["findings"], [])

    def test_rotated_cropped_page_and_form_xobject(self):
        path = self.make_document("Bus ticket", "empty", rotation=90, crop=True)
        result = analyze_content_streams(path)
        self.assertFalse(result["errors"], result)
        self.assertTrue(result["findings"])
        evidence = self.root / "rotated-evidence.pdf"
        generate_visual_evidence(path, result["findings"], evidence)
        with pymupdf.open(evidence) as document:
            red = next(d for d in document[1].get_drawings() if d.get("color") == (1, 0, 0))
            for actual, expected in zip(red["rect"], result["findings"][0]["text_bbox"]):
                self.assertAlmostEqual(actual, expected, places=3)
            self.assertEqual(document[1].rotation, 90)
        with pymupdf.open(path) as source, pymupdf.open() as target:
            target.new_page(width=900, height=900).show_pdf_page(pymupdf.Rect(50, 50, 850, 850), source, 1)
            target.save(self.root / "form.pdf")
        result = analyze_content_streams(self.root / "form.pdf")
        self.assertFalse(result["errors"], result)
        self.assertTrue(result["findings"], result)

    def test_td_and_transformed_empty_block(self):
        path = self.make_document("Flight ticket")
        with pikepdf.open(path) as pdf:
            page = pdf.pages[1]
            page.Contents = pdf.make_stream(b"q 2 0 0 2 10 20 cm BT /helv 11 Tf 31 361 Td ET Q\nBT /cour 11 Tf 1 0 0 1 72 742 Tm (sivam) Tj ET")
            # Use a distinct font resource to exercise resource-independent matching.
            page.Resources.Font['/cour'] = page.Resources.Font['/helv']
            pdf.save(self.root / "transformed.pdf")
        result = analyze_content_streams(self.root / "transformed.pdf")
        self.assertFalse(result["errors"], result)
        self.assertTrue(result["findings"], result)

    def test_incremental_edit_and_removal(self):
        for removed in (False, True):
            path = self.make_document("Letter")
            with pymupdf.open(path) as doc:
                page = doc[1]
                xref = page.get_contents()[-1]
                stream = doc.xref_stream(xref)
                new_stream = stream.replace(b"73686976616d", b"" if removed else b"736976616d")
                doc.update_stream(xref, new_stream)
                doc.saveIncr()
            result = analyze_content_streams(path)
            revision = [f for f in result["findings"] if f["evidence_type"] == "embedded_revision_text_difference"]
            self.assertTrue(revision, result)
            self.assertEqual(revision[0]["original_text"], "shivam")
            self.assertEqual(revision[0]["replacement_text"], None if removed else "sivam")
            self.assertEqual(revision[0]["location_source"], "earlier_revision" if removed else "current_revision")

    def test_regenerated_or_fully_redacted_text_leaves_no_evidence(self):
        path = self.make_document("Letter")
        with pymupdf.open(path) as doc:
            for box in doc[1].search_for("shivam"):
                doc[1].add_redact_annot(box)
            doc[1].apply_redactions()
            doc.save(self.root / "flattened.pdf", garbage=4, deflate=True)
        result = analyze_content_streams(self.root / "flattened.pdf")
        self.assertFalse(result["findings"], result)

    def test_editing_annotations(self):
        path = self.make_document("Flight boarding pass")
        with pymupdf.open(path) as doc:
            doc[1].add_freetext_annot(pymupdf.Rect(70, 85, 145, 105), "sivam")
            doc[1].add_redact_annot(pymupdf.Rect(70, 120, 145, 140))
            doc.save(self.root / "annotations.pdf")
        result = analyze_content_streams(self.root / "annotations.pdf")
        annotations = [f for f in result["findings"] if f["finding"] == "editing_annotation"]
        self.assertEqual({f["annotation_type"] for f in annotations}, {"FreeText", "Redact"})
        self.assertTrue(all(f["page"] == 2 and f["text_bbox"] for f in annotations))

    def test_partial_failures_and_summary(self):
        path = self.make_document("Invoice", "whiteout")
        with patch('app.manipulation_detector.analyze_metadata', side_effect=ValueError('test failure')):
            result = analyze_manipulation(path, self.root / 'output')
        self.assertEqual(result['status'], 'completed_with_errors')
        self.assertTrue(result['checks']['content_stream_analysis']['findings'])
        messages = [f['message'] for f in result['summary']['findings']]
        self.assertTrue(any('opaque rectangle' in message for message in messages))


if __name__ == '__main__':
    unittest.main()
