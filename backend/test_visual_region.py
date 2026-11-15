from pathlib import Path
from app.visual_region_detector import analyze_visual_regions

# Change this to the PDF you want to test
PDF_PATH = Path(r"C:\Users\KIIT0001\Downloads\document-forensics-day1-starter\document-forensics-starter\uploads\eae769ea-582e-4139-81d1-333472bd94bb.pdf")

result = analyze_visual_regions(PDF_PATH)

print("\n========== VISUAL REGION ANALYSIS ==========")

print("Technique:", result["technique"])
print("Total pages:", result["page_count"])

for page in result["pages"]:

    print(f"\nPAGE: {page['page_number']}")

    print("Text spans:", page["text_span_count"])
    print("Font anomalies:", page["font_anomaly_count"])
    print("Colour anomalies:", page["color_anomaly_count"])
    print("Text overlaps:", page["overlap_count"])
    print("Images:", page["image_count"])
    print("Text-image overlaps:", page["text_image_overlap_count"])

    if page["anomalies"]:
        print("\nAnomalies:")
        for anomaly in page["anomalies"]:
            print(anomaly)

print("\n============================================")