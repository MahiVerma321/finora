
from pathlib import Path
from pprint import pprint

from app.pdf_structure_detector import analyze_pdf_structure

PDF_PATH = Path("C:\\Users\\KIIT0001\\Downloads\\document-forensics-day1-starter\\document-forensics-starter\\uploads\\588745c9-3087-480b-b66b-cdd7c47c4825.pdf")

result = analyze_pdf_structure(PDF_PATH)

print("\n========== PDF STRUCTURAL ANALYSIS ==========")

print("Technique:", result["technique"])
print("Pages:", result["page_count"])
print("Encrypted:", result["is_encrypted"])

print("\n--- TRAILER ANALYSIS ---")
pprint(result["trailer_analysis"])

print("\n--- OBJECT ANALYSIS ---")
pprint(result["object_analysis"])

print("\n--- PAGE ANALYSIS ---")
pprint(result["page_analysis"])

print("\n--- SIGNATURE ANALYSIS ---")
pprint(result["signature_analysis"])

print("\n--- ANNOTATION OBJECT ANALYSIS ---")
pprint(result["annotation_object_analysis"])

print("\n=============================================")
