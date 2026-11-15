
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
    for date_format in DATE_FORMATS:
        try:
            datetime.strptime(str(value).strip(), date_format)
            return "passed", "Recognised date format."
        except ValueError:
            continue

    return "failed", "Date could not be parsed."


def validate_time(value):
    for time_format in TIME_FORMATS:
        try:
            datetime.strptime(str(value).strip(), time_format)
            return "passed", "Recognised time format."
        except ValueError:
            continue

    return "failed", "Time could not be parsed."



def validate_price(value):
    text = str(value).strip()

    # Remove currency labels such as Rs., INR and Rupees.
    cleaned = re.sub(
        r"(?i)\b(?:INR|RS|RUPEES)\.?",
        "",
        text
    )

    # Remove currency symbols.
    cleaned = re.sub(r"[₹,$]", "", cleaned)

    # Remove thousands separators.
    cleaned = cleaned.replace(",", "").strip()

    if re.fullmatch(r"\d+(?:\.\d{1,2})?", cleaned):
        return "passed", "Recognised numeric price."

    return "failed", "Price is not in a recognised numeric format."

def validate_flight_number(value):
    text = str(value).strip().upper()

    if re.fullmatch(r"[A-Z0-9]{2}\s?\d{1,4}[A-Z]?", text):
        return "passed", "Recognised flight-number format."

    return "failed", "Unrecognised flight-number format."


def validate_train_number(value):
    text = str(value).strip()

    if re.fullmatch(r"\d{4,6}", text):
        return "passed", "Recognised train-number format."

    return "failed", "Unrecognised train-number format."


def validate_route(fields):
    origin = get_value(fields.get("origin"))
    destination = get_value(fields.get("destination"))

    if not origin or not destination:
        return "inconclusive", "Origin or destination is missing."

    if str(origin).strip().casefold() == str(destination).strip().casefold():
        return "failed", "Origin and destination are identical."

    return "passed", "Both route fields are present and different."


def validate_extracted_fields(extraction_result):
    fields = extraction_result.get("fields", {})
    checks = []

    validators = {
        "journey_date": validate_date,
        "departure_date": validate_date,
        "arrival_date": validate_date,
        "departure_time": validate_time,
        "boarding_time": validate_time,
        "arrival_time": validate_time,
        "ticket_price": validate_price,
        "flight_number": validate_flight_number,
        "train_number": validate_train_number,
    }

    for field_name, validator in validators.items():
        if field_name not in fields:
            continue

        value = get_value(fields[field_name])

        if value is None or not str(value).strip():
            status, message = "inconclusive", "Field has no extracted value."
        else:
            status, message = validator(value)

        checks.append({
            "field": field_name,
            "value": value,
            "status": status,
            "message": message,
        })

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
