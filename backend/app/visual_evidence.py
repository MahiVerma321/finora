
import pymupdf
from pathlib import Path


def generate_visual_evidence(pdf_path, findings, output_path):
    """
    Generate a copy of the PDF with suspected
    modification areas highlighted.
    """

    pdf_path = Path(pdf_path)
    output_path = Path(output_path)

    doc = pymupdf.open(pdf_path)

    highlighted_count = 0

    for finding in findings:

        page_number = finding.get("page", 1) - 1
        bbox = finding.get("text_bbox")

        if bbox is None:
            continue

        if page_number < 0 or page_number >= len(doc):
            continue

        page = doc[page_number]

        rect = pymupdf.Rect(bbox)

        # Draw a red rectangle around the detected text
        page.draw_rect(
            rect,
            color=(1, 0, 0),
            width=2,
            overlay=True
        )

        highlighted_count += 1

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    doc.save(str(output_path), garbage=3, deflate=True)
    doc.close()

    return {
        "output_path": str(output_path),
        "highlighted_regions": highlighted_count,
        "status": "completed"
    }
