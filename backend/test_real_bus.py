import fitz
import numpy as np

from app.ocr_engine import get_ocr_engine
from app.authenticity.ticket_extractor import extract_document


PDF_PATH = r"C:\Users\KIIT0001\Downloads\TVBV33716574.pdf"


def main():
    print("Loading PDF...")

    document = fitz.open(PDF_PATH)
    engine = get_ocr_engine()

    all_lines = []

    for page_no, page in enumerate(document):
        print(f"Processing page {page_no + 1}...")

        pix = page.get_pixmap(
            matrix=fitz.Matrix(2, 2),
            alpha=False
        )

        image = np.frombuffer(
            pix.samples,
            dtype=np.uint8
        ).reshape(pix.height, pix.width, pix.n)

        results = engine.predict(image)

        for result in results:
            texts = result.get("rec_texts", [])
            scores = result.get("rec_scores", [])
            boxes = result.get("rec_polys", [])

            for i, text in enumerate(texts):
                all_lines.append({
                    "text": text,
                    "confidence": float(scores[i]),
                    "page": page_no + 1,
                    "box": boxes[i].tolist()
                })

    print("\nTotal OCR lines:", len(all_lines))

    # Run the actual document extraction pipeline
    ticket = extract_document({"lines": all_lines})

    print("\n" + "=" * 50)
    print("REAL BUS TICKET EXTRACTION")
    print("=" * 50)

    print("Document type:", ticket.get("document_type"))
    print("Issuer:", ticket.get("issuer"))

    print("\nEXTRACTED FIELDS:")

    for key, value in ticket.get("fields", {}).items():
        if isinstance(value, dict):
            print(f"{key:20}: {value.get('value')}")
        else:
            print(f"{key:20}: {value}")

    print("\nFIELD CONFLICTS:")
    print(ticket.get("observations", {}).get("field_conflicts", {}))

    print("\nFIELD COMPARISONS:")
    print(ticket.get("observations", {}).get("field_comparisons", {}))


if __name__ == "__main__":
    main()