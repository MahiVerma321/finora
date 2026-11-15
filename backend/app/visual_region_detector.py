

from pathlib import Path
from collections import Counter, defaultdict
import statistics

import pymupdf


def extract_text_spans(page):
    """Extract text spans with font, colour and position information."""

    data = page.get_text("dict")
    spans = []

    for block_index, block in enumerate(data.get("blocks", [])):
        if block.get("type") != 0:
            continue

        for line_index, line in enumerate(block.get("lines", [])):
            line_bbox = [
                round(value, 2)
                for value in line.get("bbox", [])
            ]

            for span in line.get("spans", []):
                text = span.get("text", "").strip()

                if not text:
                    continue

                origin = span.get("origin", [None, None])

                spans.append({
                    "text": text,
                    "font": span.get("font"),
                    "font_size": round(span.get("size", 0), 2),
                    "color": span.get("color"),
                    "bbox": [
                        round(value, 2)
                        for value in span.get("bbox", [])
                    ],
                    "flags": span.get("flags", 0),
                    "origin": origin,
                    "baseline": origin[1] if len(origin) > 1 else None,
                    "block_index": block_index,
                    "line_index": line_index,
                    "line_bbox": line_bbox
                })

    return spans


def detect_image_regions(page):
    image_regions = []

    page_area = page.rect.width * page.rect.height

    for image in page.get_image_info(xrefs=True):
        bbox = image.get("bbox")

        if not bbox:
            continue

        x0, y0, x1, y1 = bbox
        image_area = max(0, x1 - x0) * max(0, y1 - y0)

        image_regions.append({
            "type": "image_region",
            "bbox": [round(value, 2) for value in bbox],
            "width": image.get("width"),
            "height": image.get("height"),
            "xref": image.get("xref"),
            "page_area_ratio": round(image_area / page_area, 3)
            if page_area else 0
        })

    return image_regions


def detect_text_image_overlaps(spans, image_regions):
    anomalies = []

    for span in spans:
        x0, y0, x1, y1 = span["bbox"]
        text_area = max(0, x1 - x0) * max(0, y1 - y0)

        if text_area == 0:
            continue

        for image in image_regions:

            if image["page_area_ratio"] >= 0.60:
                continue

            a0, b0, a1, b1 = image["bbox"]

            overlap_width = max(
                0, min(x1, a1) - max(x0, a0)
            )
            overlap_height = max(
                0, min(y1, b1) - max(y0, b0)
            )

            overlap_ratio = (
                overlap_width * overlap_height
            ) / text_area

            if overlap_ratio >= 0.25:
                anomalies.append({
                    "type": "text_image_overlap",
                    "text": span["text"][:80],
                    "text_bbox": span["bbox"],
                    "image_bbox": image["bbox"],
                    "overlap_ratio": round(overlap_ratio, 3),
                    "reason": (
                        "Text significantly overlaps an embedded image. "
                        "This may be intentional and requires examination."
                    )
                })

    return anomalies


def detect_font_anomalies(spans):
    """
    Compare font sizes and families within individual text lines.

    This avoids treating the most common font on an entire page
    as the only legitimate font.
    """

    anomalies = []

    line_groups = defaultdict(list)

    for span in spans:
        key = (span["block_index"], span["line_index"])
        line_groups[key].append(span)

    for line_spans in line_groups.values():

        if len(line_spans) < 3:
            continue

        sizes = [
            span["font_size"]
            for span in line_spans
            if span["font_size"] > 0
        ]

        if len(sizes) < 3:
            continue

        median_size = statistics.median(sizes)

        for span in line_spans:
            reasons = []

            size = span["font_size"]

            if median_size > 0:
                deviation = abs(size - median_size) / median_size

                if deviation > 0.35:
                    reasons.append(
                        "Font size differs substantially from "
                        "other spans on the same line."
                    )

            if reasons:
                anomalies.append({
                    "type": "font_anomaly",
                    "text": span["text"][:100],
                    "bbox": span["bbox"],
                    "font": span["font"],
                    "font_size": size,
                    "reasons": reasons
                })

    return anomalies


def is_neutral_color(color):
    """Ignore ordinary black, white and grayscale text."""

    if color is None:
        return True

    red = (color >> 16) & 255
    green = (color >> 8) & 255
    blue = color & 255

    return (
        max(red, green, blue) - min(red, green, blue) < 15
    )


def detect_color_anomalies(spans):
    """Identify unusual non-neutral colours with contextual filtering."""

    anomalies = []

    if len(spans) < 8:
        return anomalies

    colors = Counter(
        span["color"]
        for span in spans
    )

    for span in spans:
        color = span["color"]

        if (
            colors[color] == 1
            and not is_neutral_color(color)
            and len(span["text"]) >= 4
        ):
            anomalies.append({
                "type": "color_anomaly",
                "text": span["text"][:100],
                "bbox": span["bbox"],
                "color": color,
                "reason": (
                    "An uncommon non-neutral text colour was detected. "
                    "It may represent intentional styling."
                )
            })

    return anomalies


def detect_text_overlaps(spans):
    """Detect overlapping text bounding boxes."""

    anomalies = []

    for i, first in enumerate(spans):
        x0, y0, x1, y1 = first["bbox"]

        for second in spans[i + 1:]:

            # Avoid comparing spans from the same extracted line.
            if (
                first["block_index"] == second["block_index"]
                and first["line_index"] == second["line_index"]
            ):
                continue

            a0, b0, a1, b1 = second["bbox"]

            overlap_width = min(x1, a1) - max(x0, a0)
            overlap_height = min(y1, b1) - max(y0, b0)

            if overlap_width > 1 and overlap_height > 1:
                anomalies.append({
                    "type": "text_overlap",
                    "text_1": first["text"][:80],
                    "text_2": second["text"][:80],
                    "bbox_1": first["bbox"],
                    "bbox_2": second["bbox"],
                    "reason": "Text bounding boxes overlap."
                })

    return anomalies


def detect_positioning_anomalies(spans):
    """
    Detect unusual baseline alignment and vertical spacing.

    These are candidate anomalies, not proof of editing.
    """

    anomalies = []

    line_groups = defaultdict(list)
    block_lines = defaultdict(dict)

    for span in spans:
        line_key = (span["block_index"], span["line_index"])

        line_groups[line_key].append(span)

        block_lines[span["block_index"]][span["line_index"]] = (
            span["line_bbox"]
        )

    # 1. Baseline consistency within individual lines.
    for line_spans in line_groups.values():

        if len(line_spans) < 2:
            continue

        comparable = [
            span for span in line_spans
            if span["baseline"] is not None
            and span["font_size"] > 0
        ]

        if len(comparable) < 2:
            continue

        median_size = statistics.median(
            span["font_size"] for span in comparable
        )

        # Exclude significantly different font sizes, since
        # superscripts and styled text can have different baselines.
        comparable = [
            span for span in comparable
            if abs(span["font_size"] - median_size)
            / median_size <= 0.15
        ]

        if len(comparable) < 2:
            continue

        median_baseline = statistics.median(
            span["baseline"] for span in comparable
        )

        for span in comparable:
            deviation = abs(
                span["baseline"] - median_baseline
            )

            if deviation > 1.5:
                anomalies.append({
                    "type": "baseline_anomaly",
                    "text": span["text"][:80],
                    "bbox": span["bbox"],
                    "baseline": round(span["baseline"], 2),
                    "deviation": round(deviation, 2),
                    "reason": (
                        "Text baseline differs from comparable "
                        "spans on the same line."
                    )
                })

    # 2. Unusually large vertical gaps within text blocks.
    for block_index, lines in block_lines.items():

        if len(lines) < 4:
            continue

        ordered_lines = sorted(
            lines.items(),
            key=lambda item: item[1][1]
        )

        gaps = []

        for i in range(1, len(ordered_lines)):
            previous_bbox = ordered_lines[i - 1][1]
            current_bbox = ordered_lines[i][1]

            gap = current_bbox[1] - previous_bbox[3]

            if gap >= 0:
                gaps.append(gap)

        if len(gaps) < 3:
            continue

        median_gap = statistics.median(gaps)

        # Avoid judging documents with essentially zero line gaps.
        if median_gap < 1:
            continue

        for i, gap in enumerate(gaps):

            if gap > max(median_gap * 3, median_gap + 12):
                line_index = ordered_lines[i + 1][0]

                anomalies.append({
                    "type": "vertical_spacing_anomaly",
                    "block_index": block_index,
                    "line_index": line_index,
                    "gap": round(gap, 2),
                    "median_gap": round(median_gap, 2),
                    "reason": (
                        "Unusually large vertical spacing between "
                        "consecutive text lines."
                    )
                })

    return anomalies


def analyze_visual_regions(file_path: Path):
    """Perform visual-region analysis on PDF pages."""

    document = pymupdf.open(file_path)

    page_results = []

    try:
        for page_number, page in enumerate(document, start=1):

            spans = extract_text_spans(page)
            image_regions = detect_image_regions(page)

            image_overlaps = detect_text_image_overlaps(
                spans, image_regions
            )

            font_anomalies = detect_font_anomalies(spans)
            color_anomalies = detect_color_anomalies(spans)
            overlap_anomalies = detect_text_overlaps(spans)

            positioning_anomalies = detect_positioning_anomalies(
                spans
            )

            anomalies = (
                font_anomalies
                + color_anomalies
                + overlap_anomalies
                + image_overlaps
                + positioning_anomalies
            )

            page_results.append({
                "page_number": page_number,
                "text_span_count": len(spans),
                "font_anomaly_count": len(font_anomalies),
                "color_anomaly_count": len(color_anomalies),
                "overlap_count": len(overlap_anomalies),
                "positioning_anomaly_count": len(positioning_anomalies),
                "image_count": len(image_regions),
                "text_image_overlap_count": len(image_overlaps),
                "image_overlaps": image_overlaps,
                "anomalies": anomalies
            })

    finally:
        document.close()

    total_image_count = sum(
        page["image_count"] for page in page_results
    )

    total_text_image_overlap_count = sum(
        page["text_image_overlap_count"] for page in page_results
    )

    all_image_overlaps = []

    for page in page_results:
        for overlap in page["image_overlaps"]:
            all_image_overlaps.append({
                "page_number": page["page_number"],
                **overlap
            })

    return {
        "technique": "Visual Region Analysis",
        "page_count": len(page_results),
        "pages": page_results,
        "image_count": total_image_count,
        "text_image_overlap_count": total_text_image_overlap_count,
        "interpretation": (
            "Font, colour, spacing, alignment and overlap "
            "inconsistencies are candidate forensic indicators. "
            "Normal document formatting can produce these results. "
            "They do not independently establish manipulation."
        )
    }
