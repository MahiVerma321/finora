
from pathlib import Path
import pymupdf

pdf_path = Path("test_revisions/text_modified.pdf")

doc = pymupdf.open(pdf_path)

try:
    for page_number, page in enumerate(doc, start=1):

        print(f"\n========== PAGE {page_number} ==========")

        print("\n--- TEXT OBJECTS ---")

        for block in page.get_text("dict")["blocks"]:

            if block.get("type") != 0:
                continue

            for line in block.get("lines", []):

                for span in line.get("spans", []):

                    print({
                        "text": span.get("text"),
                        "font": span.get("font"),
                        "size": span.get("size"),
                        "color": span.get("color"),
                        "bbox": span.get("bbox")
                    })

        print("\n--- CONTENT STREAMS ---")

        xrefs = page.get_contents()

        print("Content stream count:", len(xrefs))

        for xref in xrefs:

            stream = doc.xref_stream(xref)

            print(f"\nStream XREF: {xref}")

            if stream:
                print(
                    stream[:5000].decode(
                        "latin-1",
                        errors="replace"
                    )
                )

finally:
    doc.close()
