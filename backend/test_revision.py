
from pathlib import Path

from app.revision_detector import (
    inspect_revision_markers,
    analyze_prev_chain
)

pdf_path = Path(r"C:\Users\KIIT0001\Downloads\REVISION_2.pdf")

print("\n========== REVISION MARKER ANALYSIS ==========")

marker_result = inspect_revision_markers(pdf_path)

for key, value in marker_result.items():
    print(f"{key}: {value}")


print("\n========== PREVIOUS REVISION CHAIN ANALYSIS ==========")

chain_result = analyze_prev_chain(pdf_path)

for key, value in chain_result.items():
    print(f"{key}: {value}")


# DEBUG: Inspect raw PDF revision markers

with open(pdf_path, "rb") as file:
    data = file.read()

print("\n========== RAW PDF MARKER DEBUG ==========")

print("File size:", len(data))

print("Raw startxref occurrences:", data.count(b"startxref"))
print("Raw EOF occurrences:", data.count(b"%%EOF"))

# Display every occurrence of startxref
position = 0

while True:
    position = data.find(b"startxref", position)

    if position == -1:
        break

    print(
        "\nstartxref at:",
        position,
        "\nContext:",
        repr(data[position - 40:position + 80])
    )

    position += 9

# Display every occurrence of %%EOF
position = 0

while True:
    position = data.find(b"%%EOF", position)

    if position == -1:
        break

    print(
        "\nEOF at:",
        position,
        "\nContext:",
        repr(data[position - 40:position + 40])
    )

    position += 5


import pymupdf

print("\n========== XREF OFFSET INVESTIGATION ==========")

with open(pdf_path, "rb") as file:
    data = file.read()

# Inspect the beginning of the PDF
print("\n--- FIRST 300 BYTES ---")
print(repr(data[:300]))

# Inspect the location identified by startxref
print("\n--- BYTES AT OFFSET 116 ---")
print(repr(data[116:116 + 500]))

# Inspect the location referenced by /Prev
print("\n--- BYTES AT OFFSET 92219 ---")
print(repr(data[92219:92219 + 300]))

# Inspect PyMuPDF's interpretation
print("\n--- PYMUPDF TRAILER ---")

doc = pymupdf.open(pdf_path)

try:
    print(doc.pdf_trailer())
    print("\nXREF LENGTH:", doc.xref_length())
finally:
    doc.close()
