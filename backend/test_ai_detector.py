
from pathlib import Path

from app.ai_detector import analyze_ai_file


# Replace this with the name of your existing ChatGPT-generated PDF.
pdf_path = Path("test_revisions/Indian Railway Ticket Sample.pdf")

result = analyze_ai_file(pdf_path)

print("\n========== CENTRAL AI DETECTOR TEST ==========")
print("Status:", result.get("status"))
print("File type:", result.get("file_type"))
print("Analysis type:", result.get("analysis_type"))
print("Assessment:", result.get("assessment"))

pdf_analysis = result.get("pdf_analysis", {})

print("\n========== PROVENANCE ==========")
print(
    pdf_analysis
    .get("checks", {})
    .get("provenance", {})
)

print("\n========== FINDINGS ==========")
for finding in pdf_analysis.get("findings", []):
    print(finding)
