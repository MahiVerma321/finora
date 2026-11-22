from typing import Any

DOCUMENT_SCHEMAS = {

    "flight": {
        "category": "transport",
        "label": "Flight Ticket / Boarding Pass",
        "required_fields": [
            "issuer",
            "origin",
            "destination",
        ],
        "optional_fields": [
            "flight_number",
            "departure_date",
            "departure_time",
            "passenger_name",
            "seat",
            "boarding_time",
            "arrival_time",
            "ticket_price",
            "pnr",
        ],
    },
    "train": {
        "category": "transport",
        "label": "Train Ticket / Reservation Slip",
        "required_fields": [
            "issuer",
            "origin",
            "destination",
        ],
        "optional_fields": [
            "train_number",
            "train_name",
            "journey_date",
            "passenger_name",
            "departure_time",
            "arrival_time",
            "arrival_date",
            "travel_class",
            "seat",
            "ticket_price",
            "pnr",
        ],
    },
   "bus": {
    "category": "transport",
    "label": "Bus Ticket",
    "required_fields": [
        "issuer",
        "origin",
        "destination",
    ],
    "optional_fields": [
        "journey_date",
        "departure_time",
        "arrival_time",
        "arrival_date",
        "seat",
        "ticket_price",
        "passenger_name",
        "pnr",
        "ticket_number",
        "operator",
        "boarding_point",
        "dropping_point",
        "travel_class",
    ],
},
    "invoice": {
        "category": "commercial",
        "label": "Commercial Invoice",
        "required_fields": [
            "issuer",
            "invoice_number",
            "invoice_date",
            "total_amount",
        ],
        "optional_fields": [
            "customer_name",
            "due_date",
            "subtotal",
            "tax_amount",
            "currency",
        ],
    },
    "receipt": {
        "category": "commercial",
        "label": "Payment Receipt / Bill",
        "required_fields": [
            "issuer",
            "receipt_date",
            "total_amount",
        ],
        "optional_fields": [
            "receipt_number",
            "customer_name",
            "payment_method",
            "tax_amount",
        ],
    },
    "bank_statement": {
        "category": "financial",
        "label": "Bank Statement",
        "required_fields": [
            "issuer",
            "account_number",
            "statement_date",
        ],
        "optional_fields": [
            "customer_name",
            "period_start",
            "period_end",
            "opening_balance",
            "closing_balance",
        ],
    },
    "certificate": {
        "category": "official",
        "label": "Certificate / Official Credential",
        "required_fields": [
            "issuer",
            "recipient_name",
            "issue_date",
        ],
        "optional_fields": [
            "certificate_id",
            "expiry_date",
            "title",
        ],
    },
    "generic": {
        "category": "general",
        "label": "General Document",
        "required_fields": [],
        "optional_fields": [
            "issuer",
            "document_date",
            "reference_number",
            "recipient_name",
            "total_amount",
        ],
    },
}


def get_document_schema(document_type: str) -> dict:
    """Retrieve the schema definition for a document type."""
    normalized = str(document_type).lower().strip()
    return DOCUMENT_SCHEMAS.get(normalized, DOCUMENT_SCHEMAS["generic"])


def make_field(
    value: Any = None,
    confidence: float | None = None,
    page: int | None = None,
    box: list | None = None,
    source_text: str | None = None
) -> dict:
    """Standard structure for an extracted document field."""
    return {
        "value": value,
        "confidence": confidence,
        "page": page,
        "box": box,
        "source_text": source_text
    }


def make_document_record(
    document_type: str,
    issuer: str | None,
    fields: dict,
    observations: dict | None = None,
    category: str | None = None
) -> dict:
    """
    Standard schema-driven structure for extracted document data across
    all document types (tickets, invoices, receipts, statements, certificates).
    """
    normalized_type = str(document_type).lower().strip() if document_type else "generic"
    schema = get_document_schema(normalized_type)

    return {
        "document_type": normalized_type,
        "document_category": category or schema.get("category", "general"),
        "document_label": schema.get("label", "Document"),
        "issuer": issuer,
        "fields": fields,
        "observations": observations or {}
    }


def make_ticket(
    document_type: str,
    issuer: str | None,
    fields: dict,
    observations: dict | None = None
) -> dict:
    """
    Backward-compatible factory method for tickets and general documents.
    """
    return make_document_record(
        document_type=document_type,
        issuer=issuer,
        fields=fields,
        observations=observations
    )


def get_field_value(document: dict, field_name: str):
    """
    Safely retrieve a field value. Supports both direct scalar values
    and structured field dicts: {"value": ..., "confidence": ...}.
    """
    value = document.get("fields", {}).get(field_name)

    if isinstance(value, dict):
        return value.get("value")

    return value


def get_field_confidence(document: dict, field_name: str):
    value = document.get("fields", {}).get(field_name)

    if isinstance(value, dict):
        return value.get("confidence")

    return None
