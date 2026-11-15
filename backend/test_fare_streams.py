import re
from pathlib import Path

import fitz


# Replace this with your modified PDF's actual filename
pdf_path = Path("test_revisions/text_modified.pdf")

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
                rb'/(F\d+)\s+([\d.]+)\s+Tf',
                block
            )

            font_name = font.group(1).decode() if font else "Unknown"
            font_size = font.group(2).decode() if font else "Unknown"

            show_count = len(
                re.findall(rb'\bTj\b|\bTJ\b', block)
            )

            print(
                f"  Text position: x={x}, y={y}, "
                f"font={font_name}, size={font_size}, "
                f"text operators={show_count}"
            )

doc.close()

print("\n========== ANALYSIS COMPLETE ==========")