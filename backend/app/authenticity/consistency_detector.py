from datetime import datetime
from .ticket_schema import get_field_value
from app.authenticity.field_validator import validate_extracted_fields
from app.authenticity.field_validator import validate_extracted_fields

REQUIRED_FIELDS = {
    "flight": [
        "issuer",
        "flight_number",
        "origin",
        "destination",
        "departure_date",
        "departure_time",
        "passenger_name"
    ],

    "train": [
        "issuer",
        "train_number",
        "origin",
        "destination",
        "journey_date"
    ],

    "bus": [
        "issuer",
        "origin",
        "destination",
        "journey_date"
    ]
}


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

    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
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
        "%d/%B/%Y"
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def check_required_fields(ticket, checks):
    document_type = ticket.get("document_type")

    required = REQUIRED_FIELDS.get(document_type)

    if required is None:
        add_check(
            checks,
            "document_type",
            "inconclusive",
            "Unsupported or unknown ticket type.",
            "warning"
        )
        return

    missing = []

    for field in required:
        if field == "issuer":
            value = ticket.get("issuer")
        else:
            value = get_field_value(ticket, field)

        if value is None or str(value).strip() == "":
            missing.append(field)

    if missing:
        add_check(
            checks,
            "required_fields",
            "warning",
            "Missing fields: " + ", ".join(missing),
            "warning"
        )
    else:
        add_check(
            checks,
            "required_fields",
            "passed",
            "All configured required fields are present."
        )


def check_route(ticket, checks):
    origin = normalize_text(get_field_value(ticket, "origin"))
    destination = normalize_text(
        get_field_value(ticket, "destination")
    )

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



def check_repeated_fields(ticket, checks):
    """
    Compare repeated observations of the same field.

    Conflicting observations are flagged for review.
    They are not automatically treated as proof of manipulation.
    """

    observations = ticket.get(
        "observations", {}
    ).get("repeated_fields", {})

    for field_name, values in observations.items():

        if not isinstance(values, list) or len(values) < 2:
            continue

        # Ignore empty observations.
        normalized_values = [
            normalize_text(item.get("value"))
            for item in values
            if isinstance(item, dict)
            and item.get("value")
        ]

        # No useful values to compare.
        if len(normalized_values) < 2:
            continue

        unique_values = set(normalized_values)

        if len(unique_values) > 1:
            add_check(
                checks,
                f"repeated_{field_name}",
                "warning",
                (
                    f"Conflicting observations found for {field_name}. "
                    f"Values require manual verification."
                ),
                "medium"
            )

        else:
            add_check(
                checks,
                f"repeated_{field_name}",
                "passed",
                f"Repeated values for {field_name} match."
            )


def check_extraction_conflicts(ticket, checks):
    """
    Check disagreements between issuer-specific and generic extraction.

    A disagreement is a warning requiring review, not proof
    that the document has been manipulated.
    """

    observations = ticket.get("observations", {})
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
                f"Issuer-specific and generic extractors disagree "
                f"on {field_name}. "
                f"Specific: {specific_value}; "
                f"Generic: {generic_value}. "
                f"Manual verification is recommended."
            ),
            "medium"
        )

def check_date_format(ticket, checks):
    date_fields = (
        ["departure_date"]
        if ticket.get("document_type") == "flight"
        else ["journey_date"]
    )

    for field_name in date_fields:
        value = get_field_value(ticket, field_name)

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


def check_flight_times(ticket, checks):
    if ticket.get("document_type") != "flight":
        return

    boarding = parse_time(
        get_field_value(ticket, "boarding_time")
    )

    departure = parse_time(
        get_field_value(ticket, "departure_time")
    )

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



def analyze_consistency(ticket):
    checks = []

    # Existing consistency checks
    check_required_fields(ticket, checks)
    check_route(ticket, checks)
    check_repeated_fields(ticket, checks)
    check_extraction_conflicts(ticket, checks)
    check_date_format(ticket, checks)
    check_flight_times(ticket, checks)

    failed = sum(c["status"] == "failed" for c in checks)

    warnings = sum(
        c["status"] in ("warning", "inconclusive")
        for c in checks
    )

    if failed:
        overall_status = "review_required"
    elif warnings:
        overall_status = "incomplete"
    else:
        overall_status = "passed"

    consistency_report = {
        "module": "ticket_consistency",
        "status": overall_status,
        "summary": {
            "total_checks": len(checks),
            "passed": sum(
                c["status"] == "passed" for c in checks
            ),
            "failed": failed,
            "warnings": warnings
        },
        "checks": checks
    }

    # New field-format validation
    field_validation_report = validate_extracted_fields(
        ticket
    )

    
    return {
        "module": "combined_ticket_validation",

        # Backward compatibility with existing tests
        "status": overall_status,
        "summary": consistency_report["summary"],
        "checks": consistency_report["checks"],

        # Explicit status
        "overall_status": overall_status,

        # Detailed reports
        "consistency_report": consistency_report,

        "field_validation_report": {
            "module": "field_validation",
            **field_validation_report
        }
    }
