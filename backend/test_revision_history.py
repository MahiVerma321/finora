
from pathlib import Path
import pymupdf

from app.revision_detector import (
    inspect_revision_markers,
    analyze_prev_chain
)

BASE_DIR = Path("test_revisions")

FILES = [
    ("Original", BASE_DIR / "original.pdf"),
    ("Revision 1 - Comment", BASE_DIR / "revision_1.pdf"),
    ("Revision 2 - Highlight", BASE_DIR / "revision_2.pdf"),
]


def inspect_pdf(path):
    doc = pymupdf.open(path)

    try:
        result = {
            "file_size": path.stat().st_size,
            "page_count": len(doc),
            "xref_length": doc.xref_length(),
            "is_linearized": bool(__import__("re").search(rb"/Linearized\s+[\d.]+",path.read_bytes()[:1024]
    )
),
            "annotations": [],
            "text_length": 0,
        }

        for page_number, page in enumerate(doc, start=1):
            result["text_length"] += len(page.get_text())

            annotations = page.annots()

            if annotations:
                for annot in annotations:
                    result["annotations"].append({
                        "page": page_number,
                        "type": annot.type[1],
                        "content": annot.info.get("content", ""),
                    })

        return result

    finally:
        doc.close()


for label, path in FILES:
    print(f"\n========== {label.upper()} ==========")

    if not path.exists():
        print("ERROR: File not found:", path)
        continue

    print("FILE:", path.name)

    structural = inspect_pdf(path)

    for key, value in structural.items():
        print(f"{key}: {value}")

    print("\n--- REVISION MARKERS ---")
    markers = inspect_revision_markers(path)

    for key, value in markers.items():
        print(f"{key}: {value}")

    print("\n--- PREVIOUS REVISION CHAIN ---")
    chain = analyze_prev_chain(path)

    for key, value in chain.items():
        print(f"{key}: {value}")
