from datetime import datetime
import re

from .ticket_schema import get_field_value, get_document_schema
from app.authenticity.field_validator import validate_extracted_fields


def add_check(checks, name, status, message, severity="info"):
    checks.append({
        "name": name,
        "status": status,
        "severity": severity,
        "message": message
    })


def normalize_text(value):
    if value is None:
        return None
    return " ".join(str(value).strip().lower().split())


def parse_time(value):
    if not value:
        return None

    value = str(value).strip().lower()
    value = value.replace("hrs", "").strip()

    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p", "%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue

    return None


def parse_date(value):
    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d %b %Y",
        "%d %B %Y",
        "%d-%b-%Y",
        "%d-%B-%Y",
        "%d/%b/%Y",
        "%d/%B/%Y",
        "%b %d, %Y",
        "%B %d, %Y",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def parse_numeric_amount(value):
    if not value:
        return None
    cleaned = re.sub(r"(?i)\b(?:INR|RS|RUPEES|USD|EUR|GBP)\.?", "", str(value))
    cleaned = re.sub(r"[₹,$,€,£]", "", cleaned)
    cleaned = cleaned.replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None



def check_required_fields(document, checks):
    """
    Check required fields according to the detected document schema.
    Missing fields produce warnings rather than automatic failures.
    """
    document_type = document.get("document_type", "generic")
    schema = get_document_schema(document_type)
    required = schema.get("required_fields", [])

    if not required:
        fields = document.get("fields", {})

        if fields:
            add_check(
                checks,
                "document_structure",
                "passed",
                f"Document recognized as {schema.get('label', 'General Document')}; structural fields extracted."
            )
        else:
            add_check(
                checks,
                "document_structure",
                "inconclusive",
                "Limited structured fields could be extracted for this document.",
                "warning"
            )
        return

    missing = []

    for field in required:
        if field == "issuer":
            value = document.get("issuer")
        else:
            value = get_field_value(document, field)

        if value is None or str(value).strip() == "":
            missing.append(field)

    if missing:
        add_check(
            checks,
            "required_fields",
            "warning",
            "Some expected fields could not be extracted: "
            + ", ".join(missing)
            + ". Manual review is recommended.",
            "warning"
        )
    else:
        add_check(
            checks,
            "required_fields",
            "passed",
            "All configured required fields are present."
        )

def check_route(document, checks):
    """
    Validate route consistency for travel documents or any document
    containing origin and destination fields.
    """
    fields = document.get("fields", {})
    has_origin = "origin" in fields
    has_destination = "destination" in fields
    is_transport = document.get("document_type") in ("flight", "train", "bus")

    if not is_transport and not (has_origin or has_destination):
        return

    origin = normalize_text(get_field_value(document, "origin"))
    destination = normalize_text(get_field_value(document, "destination"))

    if not origin or not destination:
        add_check(
            checks,
            "route_check",
            "inconclusive",
            "Origin or destination is unavailable.",
            "warning"
        )
        return

    if origin == destination:
        add_check(
            checks,
            "route_check",
            "failed",
            "Origin and destination are identical.",
            "high"
        )
    else:
        add_check(
            checks,
            "route_check",
            "passed",
            "Origin and destination are different."
        )


def check_invoice_consistency(document, checks):
    """
    Consistency checks for commercial invoices:
    - Due date not earlier than invoice date
    - Subtotal + Tax == Total reconciliation
    """
    if document.get("document_type") != "invoice":
        return

    inv_date_val = get_field_value(document, "invoice_date")
    due_date_val = get_field_value(document, "due_date")

    if inv_date_val and due_date_val:
        inv_d = parse_date(inv_date_val)
        due_d = parse_date(due_date_val)

        if inv_d and due_d:
            if due_d < inv_d:
                add_check(
                    checks,
                    "payment_due_date",
                    "failed",
                    f"Due date ({due_date_val}) is earlier than invoice date ({inv_date_val}).",
                    "high"
                )
            else:
                add_check(
                    checks,
                    "payment_due_date",
                    "passed",
                    "Due date is on or after the invoice date."
                )

    subtotal_val = parse_numeric_amount(get_field_value(document, "subtotal"))
    tax_val = parse_numeric_amount(get_field_value(document, "tax_amount"))
    total_val = parse_numeric_amount(get_field_value(document, "total_amount"))

    if subtotal_val is not None and tax_val is not None and total_val is not None:
        expected = subtotal_val + tax_val
        tolerance = max(0.1, 0.02 * total_val)  # 2% or 0.1 rounding tolerance
        if abs(expected - total_val) <= tolerance:
            add_check(
                checks,
                "financial_reconciliation",
                "passed",
                f"Subtotal ({subtotal_val}) and tax ({tax_val}) correctly sum to total ({total_val})."
            )
        else:
            add_check(
                checks,
                "financial_reconciliation",
                "warning",
                f"Financial reconciliation discrepancy: subtotal ({subtotal_val}) + tax ({tax_val}) != total ({total_val}).",
                "medium"
            )


def check_certificate_consistency(document, checks):
    """
    Consistency checks for certificates:
    - Expiry date after issue date
    """
    if document.get("document_type") != "certificate":
        return

    issue_val = get_field_value(document, "issue_date")
    expiry_val = get_field_value(document, "expiry_date")

    if issue_val and expiry_val:
        i_date = parse_date(issue_val)
        e_date = parse_date(expiry_val)
        if i_date and e_date:
            if e_date < i_date:
                add_check(
                    checks,
                    "credential_validity_period",
                    "failed",
                    f"Expiry date ({expiry_val}) precedes issue date ({issue_val}).",
                    "high"
                )
            else:
                add_check(
                    checks,
                    "credential_validity_period",
                    "passed",
                    "Certificate validity period is chronological."
                )


def check_repeated_fields(document, checks):
    """
    Compare repeated observations of the same field across OCR spans.
    Works for any document type.
    """
    observations = document.get(
        "observations", {}
    ).get("repeated_fields", {})

    for field_name, values in observations.items():
        if not isinstance(values, list) or len(values) < 2:
            continue

        normalized_values = [
            normalize_text(item.get("value"))
            for item in values
            if isinstance(item, dict) and item.get("value")
        ]

        if len(normalized_values) < 2:
            continue

        unique_values = set(normalized_values)

        if len(unique_values) > 1:
            add_check(
                checks,
                f"repeated_{field_name}",
                "warning",
                f"Conflicting observations found for {field_name}. Manual review recommended.",
                "medium"
            )
        else:
            add_check(
                checks,
                f"repeated_{field_name}",
                "passed",
                f"Repeated values for {field_name} match."
            )


def check_extraction_conflicts(document, checks):
    """
    Check disagreements between template-specific and generic extractors.
    Works for any document type.
    """
    observations = document.get("observations", {})
    conflicts = observations.get("field_conflicts", {})

    if not isinstance(conflicts, dict) or not conflicts:
        return

    for field_name, conflict in conflicts.items():
        specific_value = conflict.get("specific_value")
        generic_value = conflict.get("generic_value")

        add_check(
            checks,
            f"extraction_conflict_{field_name}",
            "warning",
            (
                f"Extractor disagreement on {field_name}. "
                f"Specific: {specific_value}; Generic: {generic_value}. "
                f"Manual verification recommended."
            ),
            "medium"
        )


def check_date_format(document, checks):
    """
    Validate date formats for any date field present in the document.
    """
    fields = document.get("fields", {})

    date_field_names = [
        "departure_date", "journey_date", "arrival_date",
        "invoice_date", "due_date", "receipt_date",
        "statement_date", "issue_date", "expiry_date",
        "period_start", "period_end"
    ]

    for field_name in date_field_names:
        if field_name not in fields:
            continue

        value = get_field_value(document, field_name)
        if not value:
            continue

        if parse_date(value) is None:
            add_check(
                checks,
                f"{field_name}_format",
                "failed",
                f"{field_name} could not be parsed as a supported date.",
                "medium"
            )
        else:
            add_check(
                checks,
                f"{field_name}_format",
                "passed",
                f"{field_name} has a supported date format."
            )


def check_flight_times(document, checks):
    if document.get("document_type") != "flight":
        return

    boarding = parse_time(get_field_value(document, "boarding_time"))
    departure = parse_time(get_field_value(document, "departure_time"))

    if boarding is None or departure is None:
        add_check(
            checks,
            "boarding_departure_time",
            "inconclusive",
            "Boarding or departure time is missing or unreadable.",
            "warning"
        )
        return

    if boarding > departure:
        add_check(
            checks,
            "boarding_departure_time",
            "failed",
            "Boarding time is later than departure time.",
            "high"
        )
    else:
        add_check(
            checks,
            "boarding_departure_time",
            "passed",
            "Boarding time is not later than departure time."
        )


def analyze_consistency(document):
    """
    Unified schema-driven consistency analysis across all document types.
    """
    checks = []

    # 1. Structural schema compliance
    check_required_fields(document, checks)

    # 2. Domain-specific checks
    check_route(document, checks)
    check_flight_times(document, checks)
    check_invoice_consistency(document, checks)
    check_certificate_consistency(document, checks)

    # 3. Cross-document consistency checks
    check_date_format(document, checks)
    check_repeated_fields(document, checks)
    check_extraction_conflicts(document, checks)

    failed = sum(c["status"] == "failed" for c in checks)
    warnings = sum(c["status"] in ("warning", "inconclusive") for c in checks)

    if failed:
        overall_status = "review_required"
    elif warnings:
        overall_status = "incomplete"
    else:
        overall_status = "passed"

    doc_type = document.get("document_type", "document")
    schema = get_document_schema(doc_type)

    consistency_report = {
        "module": "document_consistency",
        "document_type": doc_type,
        "document_label": schema.get("label", "Document"),
        "status": overall_status,
        "summary": {
            "total_checks": len(checks),
            "passed": sum(c["status"] == "passed" for c in checks),
            "failed": failed,
            "warnings": warnings
        },
        "checks": checks
    }

    # Field-format validation
    field_validation_report = validate_extracted_fields(document)

    return {
        "module": "combined_document_validation",
        "document_type": doc_type,
        "document_label": schema.get("label", "Document"),
        "status": overall_status,
        "summary": consistency_report["summary"],
        "checks": consistency_report["checks"],
        "overall_status": overall_status,
        "consistency_report": consistency_report,
        "field_validation_report": {
            "module": "field_validation",
            **field_validation_report
        }
    }
