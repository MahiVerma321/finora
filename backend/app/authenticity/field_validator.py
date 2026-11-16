import re
from datetime import datetime


DATE_FORMATS = [
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

TIME_FORMATS = [
    "%H:%M",
    "%H:%M:%S",
    "%I:%M %p",
    "%I:%M:%S %p",
]


def get_value(field):
    if isinstance(field, dict):
        return field.get("value")
    return field


def validate_date(value):
    if value is None:
        return "inconclusive", "Date is missing."

    val_str = str(value).strip()
    for date_format in DATE_FORMATS:
        try:
            datetime.strptime(val_str, date_format)
            return "passed", "Recognised date format."
        except ValueError:
            continue

    return "failed", "Date could not be parsed."


def validate_time(value):
    if value is None:
        return "inconclusive", "Time is missing."

    val_str = str(value).strip().lower().replace("hrs", "").strip()
    for time_format in TIME_FORMATS:
        try:
            datetime.strptime(val_str, time_format)
            return "passed", "Recognised time format."
        except ValueError:
            continue

    return "failed", "Time could not be parsed."


def validate_price(value):
    if value is None:
        return "inconclusive", "Amount is missing."

    text = str(value).strip()

    # Remove currency labels such as Rs., INR, USD, EUR, etc.
    cleaned = re.sub(
        r"(?i)\b(?:INR|RS|RUPEES|USD|EUR|GBP)\.?",
        "",
        text
    )

    # Remove currency symbols.
    cleaned = re.sub(r"[₹,$,€,£]", "", cleaned)

    # Remove thousands separators.
    cleaned = cleaned.replace(",", "").strip()

    if re.fullmatch(r"-?\d+(?:\.\d{1,2})?", cleaned):
        return "passed", "Recognised numeric price or amount."

    return "failed", "Price is not in a recognised numeric format."


def validate_flight_number(value):
    if value is None:
        return "inconclusive", "Flight number is missing."

    text = str(value).strip().upper()

    if re.fullmatch(r"[A-Z0-9]{2}\s?\d{1,4}[A-Z]?", text):
        return "passed", "Recognised flight-number format."

    return "failed", "Unrecognised flight-number format."


def validate_train_number(value):
    if value is None:
        return "inconclusive", "Train number is missing."

    text = str(value).strip()

    if re.fullmatch(r"\d{4,6}", text):
        return "passed", "Recognised train-number format."

    return "failed", "Unrecognised train-number format."


def validate_invoice_number(value):
    if value is None:
        return "inconclusive", "Invoice number is missing."

    text = str(value).strip()

    if re.fullmatch(r"[A-Za-z0-9\-/_#]{2,30}", text):
        return "passed", "Recognised invoice/document identifier format."

    return "failed", "Unrecognised invoice/document identifier format."


def validate_account_number(value):
    if value is None:
        return "inconclusive", "Account number is missing."

    text = str(value).strip()

    if re.fullmatch(r"[\dX\*\-]{6,26}", text):
        return "passed", "Recognised account number format."

    return "failed", "Unrecognised account number format."


def validate_route(fields):
    origin = get_value(fields.get("origin"))
    destination = get_value(fields.get("destination"))

    if not origin or not destination:
        return "inconclusive", "Origin or destination is missing."

    if str(origin).strip().casefold() == str(destination).strip().casefold():
        return "failed", "Origin and destination are identical."

    return "passed", "Both route fields are present and different."


def validate_location(value):
    if value is None:
        return "inconclusive", "Location is missing."

    text = str(value).strip()

    if len(text) < 2:
        return "failed", "Location is too short."

    if not re.search(r"[A-Za-z]", text):
        return "failed", "Location must contain alphabetic characters."

    if not re.fullmatch(r"[A-Za-z0-9\s().,'/-]+", text):
        return "failed", "Location contains unexpected characters."

    return "passed", "Recognised location text format."


def validate_seat(value):
    if value is None:
        return "inconclusive", "Seat is missing."

    text = str(value).strip().upper()

    if re.fullmatch(r"[A-Z0-9-]{1,10}", text):
        return "passed", "Recognised seat or berth identifier format."

    return "failed", "Unrecognised seat identifier format."


FIELD_VALIDATORS = {
    # Dates
    "journey_date": validate_date,
    "departure_date": validate_date,
    "arrival_date": validate_date,
    "invoice_date": validate_date,
    "due_date": validate_date,
    "receipt_date": validate_date,
    "statement_date": validate_date,
    "issue_date": validate_date,
    "expiry_date": validate_date,
    "period_start": validate_date,
    "period_end": validate_date,

    # Times
    "departure_time": validate_time,
    "boarding_time": validate_time,
    "arrival_time": validate_time,

    # Financial / Numeric
    "ticket_price": validate_price,
    "total_amount": validate_price,
    "subtotal": validate_price,
    "tax_amount": validate_price,
    "opening_balance": validate_price,
    "closing_balance": validate_price,

    # Identifiers
    "flight_number": validate_flight_number,
    "train_number": validate_train_number,
    "invoice_number": validate_invoice_number,
    "receipt_number": validate_invoice_number,
    "account_number": validate_account_number,
    "certificate_id": validate_invoice_number,

    # Transport / Travel
    "origin": validate_location,
    "destination": validate_location,
    "seat": validate_seat,
}


def validate_extracted_fields(extraction_result):
    """
    Validate all fields present in an extraction result according
    to the generalized schema validators.
    """
    fields = extraction_result.get("fields", {})
    checks = []

    for field_name, validator in FIELD_VALIDATORS.items():
        if field_name not in fields:
            continue

        value = get_value(fields[field_name])

        if value is None or not str(value).strip():
            status, message = "inconclusive", f"{field_name} has no extracted value."
        else:
            status, message = validator(value)

        checks.append({
            "field": field_name,
            "value": value,
            "status": status,
            "message": message,
        })

    # Validate route if route fields (origin/destination) are present
    if "origin" in fields or "destination" in fields:
        route_status, route_message = validate_route(fields)
        checks.append({
            "field": "route",
            "value": {
                "origin": get_value(fields.get("origin")),
                "destination": get_value(fields.get("destination")),
            },
            "status": route_status,
            "message": route_message,
        })

    counts = {
        "passed": sum(c["status"] == "passed" for c in checks),
        "failed": sum(c["status"] == "failed" for c in checks),
        "inconclusive": sum(c["status"] == "inconclusive" for c in checks),
    }

    return {
        "checks": checks,
        "summary": counts,
    }
