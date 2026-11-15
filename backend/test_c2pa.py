
from pathlib import Path
from c2pa import Reader

# Replace this with the PDF you want to test
pdf_path = Path("test_revisions/sample_railway_ticket_bhavesh_vijay.pdf")

print("\n========== C2PA PROVENANCE TEST ==========")

if not pdf_path.exists():
    print("PDF file not found:", pdf_path)
else:
    try:
        with Reader(str(pdf_path)) as reader:
            manifest_data = reader.json()

            print("\nC2PA manifest detected!")
            print("\nEmbedded:", reader.is_embedded())
            print("\nManifest information:")
            print(manifest_data)

    except Exception as error:
        print("\nNo readable C2PA manifest was returned.")
        print("Details:", str(error))
