
import re

from app.authenticity.field_aliases import FIELD_ALIASES


def normalize_observation(value):
    if value is None:
        return ""

    value = str(value).strip().lower()
    value = re.sub(r"\s+", " ", value)

    return value.strip(" .,:;-")


def extract_matching_value(field_name, text, expected_value):
    """
    Extract the expected field value from an OCR line.
    Avoid comparing entire lines containing multiple fields.
    """

    normalized_text = normalize_observation(text)

    if field_name in ("journey_date", "departure_date", "arrival_date"):
        date_pattern = (
            r"\b\d{1,2}[-/ ](?:[A-Za-z]{3,9}|\d{1,2})[-/ ]\d{4}\b"
        )

        matches = re.findall(date_pattern, text)

        for match in matches:
            if normalize_observation(match) == expected_value:
                return match

    elif field_name in ("departure_time", "arrival_time", "boarding_time"):
        time_pattern = r"\b\d{1,2}:\d{2}\s*(?:AM|PM|hrs?)?\b"

        matches = re.findall(time_pattern, text, re.IGNORECASE)

        for match in matches:
            if normalize_observation(match) == expected_value:
                return match

    else:
        if expected_value in normalized_text:
            return expected_value

    return None


def collect_repeated_observations(lines, extracted_fields):

    observations = {}

    for field_name, extracted in extracted_fields.items():

        if not isinstance(extracted, dict):
            continue

        expected_value = normalize_observation(
            extracted.get("value")
        )

        if not expected_value:
            continue

        matched = []

        for line in lines:

            text = line.get("text", "").strip()

            if not text:
                continue

            matched_value = extract_matching_value(
                field_name,
                text,
                expected_value
            )

            if matched_value is None:
                continue

            matched.append({
                "value": matched_value,
                "confidence": line.get("confidence"),
                "page": line.get("page"),
                "box": line.get("box"),
                "source_text": text
            })

        # Remove duplicate observations at the same OCR position.
        unique = []
        seen = set()

        for item in matched:

            key = (
                normalize_observation(item["value"]),
                item["page"],
                str(item["box"])
            )

            if key not in seen:
                seen.add(key)
                unique.append(item)

        if len(unique) >= 2:
            observations[field_name] = unique

    return {
        "repeated_observations": observations,
        "observation_count": {
            field: len(values)
            for field, values in observations.items()
        }
    }
