from typing import Any


def make_field(
    value: Any = None,
    confidence: float | None = None,
    page: int | None = None,
    box: list | None = None,
    source_text: str | None = None
) -> dict:
    """
    Standard structure for an extracted ticket field.
    """
    return {
        "value": value,
        "confidence": confidence,
        "page": page,
        "box": box,
        "source_text": source_text
    }


def make_ticket(
    document_type: str,
    issuer: str | None,
    fields: dict,
    observations: dict | None = None
) -> dict:
    """
    Standard structure shared by bus, train and flight tickets.
    """

    return {
        "document_type": document_type.lower(),
        "issuer": issuer,
        "fields": fields,
        "observations": observations or {}
    }


def get_field_value(ticket: dict, field_name: str):
    """
    Safely retrieve a field value.

    Supports both:
    "origin": "Bhubaneswar"

    and:
    "origin": {"value": "Bhubaneswar", ...}
    """

    value = ticket.get("fields", {}).get(field_name)

    if isinstance(value, dict):
        return value.get("value")

    return value


def get_field_confidence(ticket: dict, field_name: str):
    value = ticket.get("fields", {}).get(field_name)

    if isinstance(value, dict):
        return value.get("confidence")

    return None