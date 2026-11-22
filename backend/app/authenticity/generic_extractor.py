
import re

from app.authenticity.field_aliases import FIELD_ALIASES
from app.authenticity.ticket_schema import make_field
from app.authenticity.spatial_matching import match_spatial_value
from app.authenticity.field_validator import FIELD_VALIDATORS

def normalize_text(text):
    """Normalize OCR text for label matching."""
    text = str(text).lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text.rstrip(":.- ")

def is_label_line(text):
    text = str(text).strip()

    for aliases in FIELD_ALIASES.values():
        for alias in aliases:
            pattern = re.compile(
                r"^\s*" + re.escape(alias) + r"(?=\s|:|-|$)",
                re.IGNORECASE
            )

            if pattern.search(text):
                return True

    return False

def extract_value_from_line(text, alias):
    """Extract a value appearing on the same line as its label."""

    pattern = re.compile(
        r"^\s*" + re.escape(alias) + r"\b\s*[:\-]?\s*(.*?)\s*$",
        re.IGNORECASE
    )

    match = pattern.match(text)

    if match and match.group(1).strip():
        return match.group(1).strip()

    return None


def is_another_label(value):
    """Prevent one field label from being extracted as another field's value."""

    normalized = normalize_text(value)

    for aliases in FIELD_ALIASES.values():
        for alias in aliases:
            if normalized == normalize_text(alias):
                return True

    return False


def validate_generic_candidate(field_name, value):
    validator = FIELD_VALIDATORS.get(field_name)

    # No specific validator: don't reject based on format.
    if validator is None:
        return True

    status, _ = validator(value)

    return status == "passed"

def extract_generic_fields(lines):
    """
    Generic ticket extraction using:
    1. Field aliases
    2. Same-line values
    3. Spatial matching
    4. Adjacent-line fallback when geometry is unavailable
    """

    extracted_fields = {}
    ambiguous_fields = {}

    alias_entries = []

    for field_name, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            alias_entries.append((field_name, alias))

    alias_entries.sort(
        key=lambda item: len(item[1]),
        reverse=True
    )

    for index, line in enumerate(lines):

        text = line.get("text", "").strip()

        if not text:
            continue

        for field_name, alias in alias_entries:

            # Do not overwrite an existing extraction.
            if field_name in extracted_fields:
                continue

            # Match labels at the beginning of the line.
            label_pattern = re.compile(
                r"^\s*" + re.escape(alias) + r"(?=\s|:|-|$)",
                re.IGNORECASE
            )

            if not label_pattern.search(text):
                continue

            # First preference: value on the same line.
            value = extract_value_from_line(text, alias)
            source_line = line

            if not value:

                # Second preference: spatial matching.
                spatial_result = match_spatial_value(line, lines)

                if spatial_result["status"] == "matched":
                    source_line = spatial_result["candidate"]
                    value = source_line.get("text", "").strip()

                elif spatial_result["status"] == "ambiguous":
                    ambiguous_fields[field_name] = {
                        "label": text,
                        "reason": spatial_result["reason"],
                        "alternatives": spatial_result.get(
                            "alternatives", []
                        )
                    }
                    continue

                else:
                    # Last resort: adjacent OCR line, but only when
                    # both lines have no usable bounding boxes.
                    if index + 1 < len(lines):
                        next_line = lines[index + 1]

                        if (
                            line.get("box") is None
                            and next_line.get("box") is None
                        ):
                            value = next_line.get("text", "").strip()
                            source_line = next_line

            if not value or is_another_label(value) or is_label_line(value):
                continue

            # Reject candidates that fail field-specific validation.
            if not validate_generic_candidate(field_name, value):
                continue

            extracted_fields[field_name] = make_field(
                value=value,
                confidence=source_line.get("confidence"),
                page=source_line.get("page"),
                box=source_line.get("box"),
                source_text=text if source_line is line else (
                    text + " | " + value
                )
            )

            break

    return {
        "fields": extracted_fields,
        "ambiguous_fields": ambiguous_fields
    }
