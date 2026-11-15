
from pathlib import Path
from app.pdf_generation_detector import analyze_pdf_generation


# Replace this with the actual name of an existing PDF
PDF_PATH = Path("C:\\Users\\KIIT0001\\Downloads\\sample_railway_ticket_bhavesh_vijay.pdf")


if not PDF_PATH.exists():
    print("PDF not found:", PDF_PATH)
else:
    result = analyze_pdf_generation(PDF_PATH)

    print("\n========== PDF GENERATION FORENSIC ANALYSIS ==========\n")

    print("Status:", result["status"])
    print("Analysis type:", result["analysis_type"])

    if result["status"] == "completed":
        for category, details in result["checks"].items():
            print(f"\n========== {category.upper()} ==========")
            print(details)

        print("\n========== FINDINGS ==========")
        for finding in result["findings"]:
            print(finding)

        print("\n========== ASSESSMENT ==========")
        print(result["assessment"])

    else:
        print("Error:", result["error"])
