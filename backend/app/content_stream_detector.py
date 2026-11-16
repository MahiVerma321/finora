
import pymupdf
import re
import os

import pikepdf
from pathlib import Path

from app.retained_revision_detector import inspect_retained_text_changes


FIELD_PATTERNS = {
    "financial": [
        "fare", "amount", "subtotal", "total",
        "grand total", "tax", "gst", "cgst",
        "sgst", "igst", "discount", "price",
        "charges", "balance", "paid"
    ],
    "identity": [
        "passenger", "customer", "guest",
        "name", "buyer", "recipient"
    ],
    "date": [
        "date", "booking date", "invoice date",
        "journey date", "travel date",
        "check-in", "check-out"
    ],
    "reference": [
        "invoice number", "invoice no",
        "booking id", "booking number",
        "pnr", "transaction id", "receipt number"
    ],
    "route_or_service": [
        "from", "to", "origin", "destination",
        "boarding", "departure", "arrival",
        "flight", "train", "bus", "room"
    ]
}



def classify_document_field(text):
    """
    Classify a document field using nearby text.
    """

    if not text:
        return {
            "category": "other",
            "matched_field_keyword": None
        }

    normalized_text = text.lower()

    for category, keywords in FIELD_PATTERNS.items():
        for keyword in keywords:

            pattern = (
                r"(?<![a-z0-9])"
                + re.escape(keyword)
                + r"(?![a-z0-9])"
            )

            if re.search(pattern, normalized_text):
                return {
                    "category": category,
                    "matched_field_keyword": keyword
                }

    return {
        "category": "other",
        "matched_field_keyword": None
    }


def get_nearby_document_context(page, bbox, max_distance=100):
    """
    Collect nearby text spans to provide context
    for document field classification.
    """

    if not bbox:
        return ""

    target_x = (bbox[0] + bbox[2]) / 2
    target_y = (bbox[1] + bbox[3]) / 2

    nearby_text = []

    page_data = page.get_text("dict")

    for block in page_data.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):

                span_bbox = span.get("bbox")

                if not span_bbox:
                    continue

                x0, y0, x1, y1 = span_bbox

                span_x = (x0 + x1) / 2
                span_y = (y0 + y1) / 2

                distance = (
                    abs(span_x - target_x)
                    + abs(span_y - target_y)
                )

                # Exclude the replacement text itself
                if distance < 5:
                    continue

                if distance <= max_distance:
                    nearby_text.append({
                        "text": span.get("text", ""),
                        "distance": distance
                    })

    nearby_text.sort(key=lambda item: item["distance"])

    return " ".join(
        item["text"] for item in nearby_text
    )


def _positioned_blocks(source, resources, initial_matrix=None, ancestors=()):
    """Interpret positioning operators, including nested Form XObjects.

    pikepdf tokenizes PDF strings and arrays so operator names inside text are
    never interpreted as instructions. Matrices use PyMuPDF's row convention.
    Text advance after a showing operator is intentionally unused: only empty
    blocks' explicit origins are compared with rendered character geometry.
    """
    matrix = initial_matrix or pymupdf.Matrix(1, 1)
    stack = []
    line_matrix = pymupdf.Matrix(1, 1)
    text_matrix = pymupdf.Matrix(1, 1)
    leading = 0.0
    block = None
    for operands, operator in pikepdf.parse_content_stream(source):
        op = str(operator)
        if op == "q":
            stack.append((matrix, leading))
        elif op == "Q" and stack:
            matrix, leading = stack.pop()
        elif op == "cm":
            matrix = pymupdf.Matrix(*map(float, operands)) * matrix
        elif op == "BT":
            line_matrix = text_matrix = pymupdf.Matrix(1, 1)
            block = {"origins": [], "has_text": False}
        elif op == "Tm":
            line_matrix = text_matrix = pymupdf.Matrix(*map(float, operands))
            if block is not None:
                block["origins"].append(pymupdf.Point(0, 0) * text_matrix * matrix)
        elif op in ("Td", "TD"):
            tx, ty = map(float, operands)
            if op == "TD":
                leading = -ty
            line_matrix = pymupdf.Matrix(1, 0, 0, 1, tx, ty) * line_matrix
            text_matrix = line_matrix
            if block is not None:
                block["origins"].append(pymupdf.Point(0, 0) * text_matrix * matrix)
        elif op == "TL":
            leading = float(operands[0])
        elif op == "T*":
            line_matrix = pymupdf.Matrix(1, 0, 0, 1, 0, -leading) * line_matrix
            text_matrix = line_matrix
        elif op in ("Tj", "TJ", "'", '"') and block is not None:
            values = operands[0] if op == "TJ" else [operands[-1]]
            if any(isinstance(value, pikepdf.String) and bytes(value) for value in values):
                block["has_text"] = True
        elif op == "ET" and block is not None:
            if not block["has_text"]:
                yield from block["origins"]
            block = None
        elif op == "Do":
            form = resources.get("/XObject", {}).get(str(operands[0]))
            if form is None or form.get("/Subtype") != "/Form":
                continue
            identity = form.objgen
            if identity in ancestors:
                raise ValueError("Recursive Form XObject cannot be inspected safely.")
            form_matrix = pymupdf.Matrix(*map(float, form.get("/Matrix", [1, 0, 0, 1, 0, 0])))
            yield from _positioned_blocks(
                form, form.get("/Resources", resources), form_matrix * matrix,
                ancestors + (identity,)
            )


def _span_text(span):
    return "".join(chr(char[0]) for char in span["chars"])


def _finding(page_number, kind, bbox, message, **details):
    return {
        "page": page_number,
        "technique": "PDF Content Stream Analysis",
        "finding": kind,
        "severity": "review",
        "evidence_type": "single_document_editing_indicator",
        "text_bbox": list(bbox),
        "interpretation": message,
        **details,
    }


def _covered_text_findings(page, spans, page_number, minimum_coverage):
    """Locate text painted before a later opaque rectangular fill.

    Backgrounds drawn before text and translucent highlights are excluded.
    These observations can also arise from intentional document design.
    """
    findings = []
    for drawing in page.get_drawings():
        if drawing.get("fill") is None or drawing.get("fill_opacity", 0) < 1:
            continue
        items = drawing.get("items", [])
        if len(items) != 1 or items[0][0] != "re":
            continue
        rectangle = pymupdf.Rect(items[0][1])
        covered = []
        for span in spans:
            if span["seqno"] >= drawing["seqno"] or span.get("type") == 3:
                continue
            for char in span["chars"]:
                box = pymupdf.Rect(char[3])
                if chr(char[0]).isspace() or box.is_empty:
                    continue
                if (box & rectangle).get_area() / box.get_area() >= minimum_coverage:
                    covered.append(char)
        if not covered:
            continue
        bounds = pymupdf.Rect(covered[0][3])
        for char in covered[1:]:
            bounds |= pymupdf.Rect(char[3])
        replacement = [span for span in spans if span["seqno"] > drawing["seqno"]
                       and span.get("type") != 3 and (pymupdf.Rect(span["bbox"]) & rectangle).get_area() > 0]
        findings.append(_finding(
            page_number, "text_covered_by_later_rectangle", bounds,
            "A later opaque rectangle covers earlier text. Review this region for intentional masking or editing.",
            covered_text="".join(chr(char[0]) for char in covered),
            replacement_text=" ".join(_span_text(span) for span in replacement) or None,
            covering_bbox=list(rectangle), drawing_sequence=drawing["seqno"],
        ))
    return findings


def analyze_content_streams(pdf_path):
    tolerance = float(os.getenv("TEXT_POSITION_TOLERANCE", "2"))
    coverage = float(os.getenv("TEXT_COVERAGE_THRESHOLD", "0.9"))
    if not 0 < tolerance <= 20 or not 0 < coverage <= 1:
        raise ValueError("Invalid text position tolerance or coverage threshold.")
    findings = []
    errors = []
    with pymupdf.open(pdf_path) as doc, pikepdf.open(pdf_path) as pdf:
        try:
            findings.extend(inspect_retained_text_changes(Path(pdf_path), doc))
        except Exception as error:
            errors.append({"module": "retained_revisions", "error": str(error)})
        for page_number, page in enumerate(doc, start=1):
            spans = page.get_texttrace()
            for annotation in page.annots() or []:
                if annotation.type[0] in (pymupdf.PDF_ANNOT_REDACT, pymupdf.PDF_ANNOT_FREE_TEXT):
                    findings.append(_finding(
                        page_number, "editing_annotation", annotation.rect,
                        f"A {annotation.type[1]} annotation is present in this region. Review its purpose and visible content.",
                        evidence_source="pdf_annotation", annotation_type=annotation.type[1],
                    ))
            # Text traces use unrotated, crop-relative coordinates. PyMuPDF's
            # transformation matrix for rotated cropped pages differs, so obtain
            # the unrotated matrix and restore rotation immediately in memory.
            rotation = page.rotation
            try:
                page.set_rotation(0)
                coordinate_matrix = page.transformation_matrix
            finally:
                page.set_rotation(rotation)
            findings.extend(_covered_text_findings(page, spans, page_number, coverage))
            try:
                source = pdf.pages[page_number - 1]
                for origin in _positioned_blocks(source, source.Resources):
                    point = origin * coordinate_matrix
                    for span in spans:
                        if span.get("type") == 3 or not span["chars"]:
                            continue
                        start = pymupdf.Point(span["chars"][0][2])
                        if abs(start.x - point.x) > tolerance or abs(start.y - point.y) > tolerance:
                            continue
                        bbox = list(span["bbox"])
                        context = get_nearby_document_context(page, bbox)
                        field_info = classify_document_field(context or _span_text(span))
                        findings.append(_finding(
                            page_number, "possible_text_replacement", bbox,
                            "An empty text block and rendered text share a position. This can be an editing trace and requires review.",
                            original_text=None, replacement_text=_span_text(span),
                            position={"x": point.x, "y": point.y},
                            coordinate_space="unrotated_page", nearby_context=context,
                            **field_info,
                        ))
            except Exception as error:
                errors.append({"page": page_number, "error": str(error)})
    # The same painted span can match multiple redundant empty blocks.
    unique = {}
    for finding in findings:
        key = (finding["page"], finding["finding"], tuple(round(v, 2) for v in finding["text_bbox"]))
        unique.setdefault(key, finding)
    return {
        "technique": "PDF Content Stream Analysis",
        "findings": list(unique.values()),
        "errors": errors,
        "status": "completed_with_errors" if errors else ("review_required" if unique else "no_matching_pattern"),
        "rules": {"position_tolerance_points": tolerance, "minimum_character_coverage": coverage},
        "limitations": "Inspects retained text operators and paint order. Flattened scans and edits that erase their traces can be inconclusive.",
    }
