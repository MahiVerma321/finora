
import pymupdf
import re


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


def extract_nearby_text(page, x, y):
    """
    Extract visible text near a PDF content-stream position.
    PDF stream coordinates usually use a bottom-left origin,
    while PyMuPDF text bounding boxes use a top-left origin.
    """

    page_height = page.rect.height
    target_y = page_height - y

    candidates = []

    page_data = page.get_text("dict")

    for block in page_data.get("blocks", []):
        for line in block.get("lines", []):
            for span in line.get("spans", []):

                bbox = span.get("bbox")

                if not bbox:
                    continue

                x0, y0, x1, y1 = bbox

                horizontal_distance = abs(x0 - x)
                vertical_distance = abs(((y0 + y1) / 2) - target_y)

                if horizontal_distance < 15 and vertical_distance < 15:
                    candidates.append({
                        "text": span.get("text", ""),
                        "font_name": span.get("font"),
                        "font_size": span.get("size"),
                        "bbox": list(bbox),
                        "distance": horizontal_distance + vertical_distance
                    })

    candidates.sort(key=lambda item: item["distance"])

    return candidates[0] if candidates else None


def analyze_content_streams(pdf_path):

    doc = pymupdf.open(pdf_path)
    findings = []

    try:
        for page_number, page in enumerate(doc, start=1):

            contents = page.get_contents()

            empty_blocks = []
            text_blocks = []

            for xref in contents:

                stream = doc.xref_stream(xref)

                if not stream:
                    continue

                blocks = re.findall(
                    rb'\bBT\b(.*?)\bET\b',
                    stream,
                    re.DOTALL
                )

                for block in blocks:

                    matrix = re.search(
                        rb'1\s+0\s+0\s+1\s+(-?[\d.]+)\s+(-?[\d.]+)\s+Tm',
                        block
                    )

                    if not matrix:
                        continue

                    x = float(matrix.group(1))
                    y = float(matrix.group(2))

                    font = re.search(
                        rb'/([A-Za-z0-9]+)\s+([\d.]+)\s+Tf',
                        block
                    )

                    if not font:
                        continue

                    item = {
                        "xref": xref,
                        "x": x,
                        "y": y,
                        "font": font.group(1).decode(
                            "latin-1", errors="replace"
                        ),
                        "size": float(font.group(2))
                    }

                    has_text = bool(
                        re.search(rb'\bTj\b|\bTJ\b', block)
                    )

                    if has_text:
                        text_blocks.append(item)
                    else:
                        empty_blocks.append(item)

            for empty in empty_blocks:

                for text in text_blocks:

                    same_position = (
                        abs(empty["x"] - text["x"]) < 2
                        and abs(empty["y"] - text["y"]) < 2
                    )

                    separate_stream = (
                        empty["xref"] != text["xref"]
                    )

                    same_font = (
                        empty["font"] == text["font"]
                    )

                    if same_position and separate_stream and same_font:

                        extracted = extract_nearby_text(
                            page,
                            text["x"],
                            text["y"]
                        )

                        context_text = get_nearby_document_context(
                            page,
                            extracted["bbox"] if extracted else None
                        )

                        field_info = classify_document_field(context_text)

                        field_info = classify_document_field(
                            extracted["text"] if extracted else None
                        )

                        findings.append({
                            "page": page_number,
                            "technique": "PDF Content Stream Analysis",
                            "finding": "possible_text_replacement",
                            "severity": "warning",

                            "original_stream": empty["xref"],
                            "replacement_stream": text["xref"],

                            "original_text": None,

                            "replacement_text": (
                                extracted["text"] if extracted else None
                            ),

                            "field_category": field_info["category"],
                            "matched_field_keyword": field_info["matched_field_keyword"],
                            "nearby_context": context_text,

                            "position": {
                                "x": text["x"],
                                "y": text["y"]
                            },

                            "font": {
                                "resource": text["font"],
                                "size": text["size"],
                                "extracted_font_name": (
                                    extracted["font_name"] if extracted else None
                                ),
                                "extracted_font_size": (
                                    extracted["font_size"] if extracted else None
                                )
                            },

                            "text_bbox": (
                                extracted["bbox"] if extracted else None
                            ),

                            "interpretation": (
                                "An empty text block and a separate "
                                "text-showing object were found at "
                                "nearly identical coordinates. "
                                "Nearby visible text was extracted "
                                "where possible. This pattern requires "
                                "manual review and is not proof of manipulation."
                            )
                        })

        return {
            "technique": "PDF Content Stream Analysis",
            "findings": findings,
            "status": (
                "review_required" if findings
                else "no_matching_pattern"
            )
        }

    finally:
        doc.close()
