from pathlib import Path
import re

try:
    import fitz
except ImportError:
    fitz = None


def main():
    if fitz is None:
        print("fitz/pymupdf not installed; skipping fare streams test script.")
        return

    pdf_path = Path("test_revisions/text_modified.pdf")
    if not pdf_path.exists():
        print(f"File not found: {pdf_path}")
        return

    doc = fitz.open(pdf_path)
    page = doc[0]

    print("\n========== FARE CONTENT STREAM ANALYSIS ==========")

    for xref in page.get_contents():
        stream = doc.xref_stream(xref)

        print(f"\nStream XREF: {xref}")
        print(f"Stream length: {len(stream)} bytes")
        print(f"BT operators: {len(re.findall(rb'\bBT\b', stream))}")
        print(f"Tj operators: {len(re.findall(rb'\bTj\b', stream))}")
        print(f"TJ operators: {len(re.findall(rb'\bTJ\b', stream))}")

        blocks = re.findall(rb'\bBT\b(.*?)\bET\b', stream, re.DOTALL)

        for block in blocks:
            matrix = re.search(
                rb'1\s+0\s+0\s+1\s+(-?[\d.]+)\s+(-?[\d.]+)\s+Tm',
                block
            )

            if not matrix:
                continue

            x = float(matrix.group(1))
            y = float(matrix.group(2))

            # Inspect only the fare area.
            if 430 <= y <= 475:
                font = re.search(
                    rb'/([A-Za-z0-9]+)\s+([\d.]+)\s+Tf',
                    block
                )

                print({
                    "stream": xref,
                    "x": x,
                    "y": y,
                    "font": font.group(1).decode() if font else None,
                    "has_text": bool(re.search(rb'\bTj\b|\bTJ\b', block))
                })

    doc.close()


if __name__ == "__main__":
    main()
