def get_box_bounds(box):
    """Convert an OCR polygon into x/y boundaries."""

    if not box:
        return None

    try:
        xs = [float(point[0]) for point in box]
        ys = [float(point[1]) for point in box]

        return {
            "left": min(xs),
            "right": max(xs),
            "top": min(ys),
            "bottom": max(ys),
            "width": max(xs) - min(xs),
            "height": max(ys) - min(ys),
        }

    except (TypeError, ValueError, IndexError):
        return None


def overlap_ratio(start1, end1, start2, end2):
    """Calculate how much two intervals overlap."""

    overlap = max(
        0,
        min(end1, end2) - max(start1, start2)
    )

    smaller_length = min(end1 - start1, end2 - start2)

    if smaller_length <= 0:
        return 0

    return overlap / smaller_length


def calculate_spatial_score(label_box, value_box):
    """
    Lower score means a more likely label-value relationship.
    Returns None when the candidate is geometrically unsuitable.
    """

    label_height = max(label_box["height"], 1)

    # Candidate to the right of the label.
    horizontal_gap = value_box["left"] - label_box["right"]

    vertical_alignment = overlap_ratio(
        label_box["top"],
        label_box["bottom"],
        value_box["top"],
        value_box["bottom"]
    )

    if (
        horizontal_gap >= -label_height * 0.25
        and vertical_alignment >= 0.3
        and horizontal_gap <= label_height * 8
    ):
        gap = max(0, horizontal_gap) / label_height
        return gap + (1 - vertical_alignment) * 1.5

    # Candidate below the label.
    vertical_gap = value_box["top"] - label_box["bottom"]

    horizontal_alignment = overlap_ratio(
        label_box["left"],
        label_box["right"],
        value_box["left"],
        value_box["right"]
    )

    if (
        vertical_gap >= -label_height * 0.25
        and horizontal_alignment >= 0.25
        and vertical_gap <= label_height * 5
    ):
        gap = max(0, vertical_gap) / label_height
        return gap + (1 - horizontal_alignment) * 1.5

    return None


def match_spatial_value(label_line, lines):
    """
    Find the most likely OCR value near a label.

    Returns matched, ambiguous, or no_match.
    """

    label_box = get_box_bounds(label_line.get("box"))

    if label_box is None:
        return {
            "status": "no_match",
            "candidate": None,
            "reason": "Label has no usable bounding box."
        }

    candidates = []

    for line in lines:

        # Do not compare a line with itself.
        if line is label_line:
            continue

        text = line.get("text", "").strip()

        if not text:
            continue

        # Do not use a value from a different page.
        if line.get("page") != label_line.get("page"):
            continue

        value_box = get_box_bounds(line.get("box"))

        if value_box is None:
            continue

        score = calculate_spatial_score(
            label_box,
            value_box
        )

        if score is not None:
            candidates.append({
                "line": line,
                "score": round(score, 3)
            })

    if not candidates:
        return {
            "status": "no_match",
            "candidate": None,
            "reason": "No suitable nearby OCR value found."
        }

    candidates.sort(key=lambda item: item["score"])

    best = candidates[0]

    # If two candidates are nearly equally close,
    # do not silently select one.
    if (
        len(candidates) > 1
        and candidates[1]["score"] - best["score"] < 0.35
    ):
        return {
            "status": "ambiguous",
            "candidate": None,
            "reason": "Multiple nearby values have similar spatial scores.",
            "alternatives": [
                {
                    "text": item["line"]["text"],
                    "score": item["score"]
                }
                for item in candidates[:3]
            ]
        }

    return {
        "status": "matched",
        "candidate": best["line"],
        "score": best["score"],
        "reason": "Nearest geometrically suitable value selected."
    }