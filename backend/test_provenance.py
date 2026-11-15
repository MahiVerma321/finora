from app.provenance_detector import analyze_provenance

pdf_path = "test_revisions/sample_railway_ticket_bhavesh_vijay.pdf"

result = analyze_provenance(pdf_path)

print("\n========== PROVENANCE ANALYSIS ==========")

import json
print(json.dumps(result, indent=4))