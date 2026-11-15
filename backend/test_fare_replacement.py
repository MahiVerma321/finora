import re
from pathlib import Path

import pymupdf


pdf_path = Path("test_revisions/text_modified.pdf")

doc = pymupdf.open(pdf_path)
page = doc[0]

print("\n========== FARE REPLACEMENT INVESTIGATION ==========")

for xref in page.get_contents():

    stream = doc.xref_stream(xref)

    print(f"\n--- CONTENT STREAM {xref} ---")

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

        if abs(x - 271) < 2 and abs(y - 448) < 2:

            print(f"Position: x={x}, y={y}")

            print(
                "Text-showing operators:",
                len(re.findall(rb'\bTj\b|\bTJ\b', block))
            )

            print("PDF operators:")

            operators = re.findall(
                rb'/[A-Za-z0-9]+\s+[\d.]+\s+Tf'
                rb'|[-\d.]+\s+[-\d.]+\s+Td'
                rb'|[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+Tm'
                rb'|Tj|TJ|Tr|Tc|Tw|Tz|Ts',
                block
            )

            for operator in operators:
                print(" ", operator.decode("latin-1"))

            print("Raw block length:", len(block), "bytes")

doc.close()

print("\n========== INVESTIGATION COMPLETE ==========")