"""Draw evidence outlines in unrotated page coordinates without altering uploads."""
import math
from pathlib import Path

import pymupdf


def generate_visual_evidence(pdf_path, findings=None, output_path=None, visual_anomalies=None):
    output_path = Path(output_path)
    counts = {"content_stream_regions": 0, "visual_anomaly_regions": 0}
    groups = [
        (findings or [], "text_bbox", (1, 0, 0), None, "content_stream_regions"),
        (visual_anomalies or [], "bbox", (0.95, 0.55, 0), "[3 2]", "visual_anomaly_regions"),
    ]
    with pymupdf.open(pdf_path) as doc:
        seen = set()
        for items, box_key, color, dashes, count_key in groups:
            for item in items:
                number = item.get("page")
                box = item.get(box_key)
                if type(number) is not int or not 1 <= number <= len(doc):
                    continue
                if not isinstance(box, (list, tuple)) or len(box) != 4:
                    continue
                if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in box):
                    continue
                page = doc[number - 1]
                bounds = page.rect * page.derotation_matrix
                rect = pymupdf.Rect(box) & bounds
                key = (number, tuple(rect), color)
                if rect.is_empty or key in seen:
                    continue
                seen.add(key)
                # Drawing also needs the unrotated transform for cropped pages.
                rotation = page.rotation
                try:
                    page.set_rotation(0)
                    page.draw_rect(rect, color=color, width=1.5, dashes=dashes, overlay=True)
                finally:
                    page.set_rotation(rotation)
                counts[count_key] += 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        doc.save(str(output_path), garbage=3, deflate=True)
    total = sum(counts.values())
    return {
        "output_path": str(output_path), "highlighted_regions": total,
        **counts, "status": "completed" if total else "no_regions_detected",
    }
