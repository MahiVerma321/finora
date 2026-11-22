
import re
from copy import deepcopy

from app.authenticity.field_validator import FIELD_VALIDATORS


def normalize_value(value):
    if value is None:
        return ""

    text = str(value).strip().lower()
    text = re.sub(r"\s+", " ", text)

    return text.strip(" .,:;-")


def get_confidence(field):
    if not isinstance(field, dict):
        return None

    confidence = field.get("confidence")

    try:
        return float(confidence) if confidence is not None else None
    except (TypeError, ValueError):
        return None


def get_value(field):
    if isinstance(field, dict):
        return field.get("value")

    return field


def validate_field(field_name, field):
    value = get_value(field)

    validator = FIELD_VALIDATORS.get(field_name)

    if validator is None:
        return "inconclusive", "No field-specific validator available."

    if value is None or not str(value).strip():
        return "inconclusive", "No value available."

    return validator(value)


def merge_fields(specific_fields, generic_fields):

    merged_fields = deepcopy(specific_fields)

    conflicts = {}
    comparisons = {}
    validations = {}

    all_field_names = (
        set(specific_fields.keys()) |
        set(generic_fields.keys())
    )

    for field_name in all_field_names:

        specific = specific_fields.get(field_name)
        generic = generic_fields.get(field_name)

        # Generic extractor found a new field.
        if specific is None:

            generic_validation = validate_field(
                field_name, generic
            )

            if generic_validation[0] == "failed":
                comparisons[field_name] = "generic_rejected"

                validations[field_name] = {
                    "generic": {
                        "status": generic_validation[0],
                        "message": generic_validation[1],
                    }
                }

                continue

            merged_fields[field_name] = deepcopy(generic)
            comparisons[field_name] = "generic_only"

            validations[field_name] = {
                "generic": {
                    "status": generic_validation[0],
                    "message": generic_validation[1],
                }
            }

            continue

        # Specific extractor found a new field.
        if generic is None:
            comparisons[field_name] = "specific_only"
            continue

        specific_value = get_value(specific)
        generic_value = get_value(generic)

        specific_validation = validate_field(
            field_name, specific
        )

        generic_validation = validate_field(
            field_name, generic
        )

        validations[field_name] = {
            "specific": {
                "status": specific_validation[0],
                "message": specific_validation[1],
            },
            "generic": {
                "status": generic_validation[0],
                "message": generic_validation[1],
            },
        }

        # Both extractors agree.
        if normalize_value(specific_value) == normalize_value(generic_value):
            comparisons[field_name] = "matched"
            continue

        # Extractors disagree.
        specific_confidence = get_confidence(specific)
        generic_confidence = get_confidence(generic)

        conflicts[field_name] = {
            "specific_value": specific_value,
            "generic_value": generic_value,
            "specific_confidence": specific_confidence,
            "generic_confidence": generic_confidence,
            "specific_validation": specific_validation[0],
            "generic_validation": generic_validation[0],
            "status": "review_required",
        }

        comparisons[field_name] = "conflict"

    return {
        "fields": merged_fields,
        "comparisons": comparisons,
        "validations": validations,
        "conflicts": conflicts,
    }

