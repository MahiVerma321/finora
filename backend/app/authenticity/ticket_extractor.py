
import re

from .ticket_schema import make_field, make_ticket
from app.authenticity.generic_extractor import extract_generic_fields
from app.authenticity.field_merger import merge_fields
from app.authenticity.observation_collector import (
    collect_repeated_observations
)

def get_line(lines, pattern):
    """Find the first OCR line matching a regular expression."""
    for line in lines:
        if re.search(pattern, line.get("text", ""), re.IGNORECASE):
            return line
    return None


def get_next_line(lines, pattern):
    """Get the first non-empty OCR line after a matching label."""
    for index, line in enumerate(lines):
        if re.search(pattern, line.get("text", ""), re.IGNORECASE):
            for following in lines[index + 1:]:
                if following.get("text", "").strip():
                    return following
    return None


def create_field(value, source_line=None):
    """Preserve the OCR evidence behind an extracted value."""
    if not value:
        return make_field()

    return make_field(
        value=str(value).strip(),
        confidence=(
            source_line.get("confidence")
            if source_line else None
        ),
        page=source_line.get("page") if source_line else None,
        box=source_line.get("box") if source_line else None,
        source_text=(
            source_line.get("text")
            if source_line else None
        )
    )


def detect_document_type(text):
    text_lower = text.lower()

    if "electronic reservation slip" in text_lower or "irctc" in text_lower:
        return "train"

    if "boarding pass" in text_lower or "indigo" in text_lower:
        return "flight"

    if "redbus" in text_lower or "ticket information" in text_lower:
        return "bus"

    return "unknown"


def extract_flight(lines):
    fields = {}

    # Airline
    airline_line = get_line(lines, r"\bIndiGo\b")

    # Flight number
    flight_line = get_line(
        lines,
        r"^\s*[A-Z0-9]{2}\s*\d{3,4}\s*$"
    )

    # Route
    route_line = get_line(
        lines,
        r"\b[A-Z][A-Z ]+\s*\([^)]*\)\s*To\s*[A-Z][A-Z ]+"
    )

    if route_line:
        match = re.search(
            r"(.+?)\s+To\s+(.+)",
            route_line["text"],
            re.IGNORECASE
        )

        if match:
            origin = re.sub(r"\s*\([^)]*\)", "", match.group(1)).strip()
            destination = re.sub(r"\s*\([^)]*\)", "", match.group(2)).strip()

            fields["origin"] = create_field(origin, route_line)
            fields["destination"] = create_field(destination, route_line)

    # Flight number
    if flight_line:
        fields["flight_number"] = create_field(
            flight_line["text"], flight_line
        )

    # Date
    date_line = get_line(
        lines,
        r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b"
    )

    if date_line:
        match = re.search(
            r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b",
            date_line["text"]
        )
        fields["departure_date"] = create_field(
            match.group(0), date_line
        )

    # Boarding time
    boarding_line = get_line(
        lines,
        r"\b\d{1,2}:\d{2}\s*hrs?\b"
    )

    if boarding_line:
        match = re.search(
            r"\d{1,2}:\d{2}",
            boarding_line["text"]
        )
        fields["boarding_time"] = create_field(
            match.group(0), boarding_line
        )

    # Departure time
    departure_line = get_line(
        lines,
        r"\bDeparture\s+\d{1,2}:\d{2}"
    )

    if departure_line:
        match = re.search(
            r"\d{1,2}:\d{2}",
            departure_line["text"]
        )
        fields["departure_time"] = create_field(
            match.group(0), departure_line
        )

        # Seat extraction
    seat_label_index = None

    for index, line in enumerate(lines):
        if re.search(r"\bSeat\b", line["text"], re.IGNORECASE):
            seat_label_index = index
            break

    if seat_label_index is not None:

        # Check the label line and nearby OCR lines.
        start = max(0, seat_label_index - 1)
        end = min(len(lines), seat_label_index + 7)

        seat_pattern = re.compile(
            r"^\s*(?:Seat\s*[:\-]?\s*)?([1-9]|[1-5]\d|60)([A-F])\s*$",
            re.IGNORECASE
        )

        for candidate in lines[start:end]:
            match = seat_pattern.fullmatch(candidate["text"])

            if match:
                fields["seat"] = create_field(
                    match.group(1) + match.group(2).upper(),
                    candidate
                )
                break

    # Passenger name in airline boarding-pass format
    passenger_line = get_line(
        lines,
        r"\b[A-Z]+/[A-Z]+/(?:MR|MRS|MS)\b"
    )

    if passenger_line:
        fields["passenger_name"] = create_field(
            passenger_line["text"], passenger_line
        )

    return make_ticket(
        "flight",
        "IndiGo",
        fields
    )



def extract_train(lines):
    fields = {}

    # Helper: find a station value associated with a label.
    def extract_station(label_pattern):
        for line in lines:
            text = line.get("text", "").strip()

            if not re.search(label_pattern, text, re.IGNORECASE):
                continue

            # Avoid accepting the label itself as the station.
            inline_match = re.search(
                label_pattern + r"\s*[:*-]?\s*(.+)$",
                text,
                re.IGNORECASE
            )

            if inline_match:
                value = inline_match.group(1).strip()

                if value and not re.fullmatch(
                    r"Boarding At|To|From|Journey Date",
                    value,
                    re.IGNORECASE
                ):
                    return create_field(value, line)

            # Try spatial matching when the label has no inline value.
            from app.authenticity.spatial_matching import match_spatial_value

            spatial_result = match_spatial_value(line, lines)

            if spatial_result["status"] == "matched":
                candidate = spatial_result["candidate"]
                candidate_text = candidate.get("text", "").strip()

                if candidate_text and not re.fullmatch(
                    r"Boarding At|To|From|Journey Date",
                    candidate_text,
                    re.IGNORECASE
                ):
                    return create_field(candidate_text, candidate)

        return None

    # Train number and name
    train_line = get_line(
        lines,
        r"\b\d{4,5}\s*/\s*[A-Z][A-Z0-9 ]+"
    )

    if train_line:
        match = re.search(
            r"\b(\d{4,5})\s*/\s*(.+)",
            train_line["text"]
        )

        if match:
            fields["train_number"] = create_field(
                match.group(1), train_line
            )
            fields["train_name"] = create_field(
                match.group(2).strip(), train_line
            )

    # Boarding station
    origin = extract_station(r"^\s*Boarding At\b")

    if origin:
        fields["origin"] = origin

    # Destination station
    destination = extract_station(r"^\s*To\b")

    if destination:
        fields["destination"] = destination

    # Journey date
    date_line = get_line(
        lines,
        r"Start Date\s*\*?\s*\d{1,2}[-/]\w+[-/]\d{4}"
    )

    if date_line:
        match = re.search(
            r"\d{1,2}[-/]\w+[-/]\d{4}",
            date_line["text"]
        )

        if match:
            fields["journey_date"] = create_field(
                match.group(0), date_line
            )

    # Departure
    departure_line = get_line(
        lines,
        r"Departure\s*\*?\s*\d{1,2}:\d{2}"
    )

    if departure_line:
        match = re.search(
            r"Departure\s*\*?\s*(\d{1,2}:\d{2})",
            departure_line["text"],
            re.IGNORECASE
        )

        if match:
            fields["departure_time"] = create_field(
                match.group(1), departure_line
            )

    # Arrival
    arrival_line = get_line(
        lines,
        r"Arrival\s*\*?\s*\d{1,2}:\d{2}"
    )

    if arrival_line:
        match = re.search(
            r"Arrival\s*\*?\s*(\d{1,2}:\d{2})",
            arrival_line["text"],
            re.IGNORECASE
        )

        if match:
            fields["arrival_time"] = create_field(
                match.group(1), arrival_line
            )

        date_match = re.search(
            r"\d{1,2}:\d{2}\s+(\d{1,2}[-/]\w+[-/]\d{4})",
            arrival_line["text"]
        )

        if date_match:
            fields["arrival_date"] = create_field(
                date_match.group(1), arrival_line
            )

    # Class
    class_line = get_line(
        lines,
        r"SECOND AC|FIRST AC|THIRD AC|SLEEPER"
    )

    if class_line:
        fields["travel_class"] = create_field(
            class_line["text"], class_line
        )

    return make_ticket(
        "train",
        "IRCTC",
        fields
    )

def extract_bus(lines):
    fields = {}

    # Journey date and time
    journey_line = get_next_line(
        lines,
        r"Journey Date and Time"
    )

    if journey_line:
        match = re.search(
            r"(\d{1,2}/\d{1,2}/\d{4}),?\s*(\d{1,2}:\d{2}\s*[AP]M)?",
            journey_line["text"],
            re.IGNORECASE
        )

        if match:
            fields["journey_date"] = create_field(
                match.group(1), journey_line
            )

            if match.group(2):
                fields["departure_time"] = create_field(
                    match.group(2), journey_line
                )

    # Boarding point
    boarding_line = get_next_line(
        lines,
        r"^\s*Boarding Point\s*$"
    )

    if boarding_line:
        fields["origin"] = create_field(
            boarding_line["text"], boarding_line
        )

    # Dropping point
    dropping_line = get_next_line(
        lines,
        r"^\s*Dropping Point\s*$"
    )

    if dropping_line:
        fields["destination"] = create_field(
            dropping_line["text"], dropping_line
        )

    # Bus operator
    operator_line = get_next_line(
        lines,
        r"^\s*Travels\s*$"
    )

    if operator_line:
        fields["operator"] = create_field(
            operator_line["text"], operator_line
        )

    # Ticket price
    price_line = get_line(
        lines,
        r"Ticket Price"
    )

    if price_line:
        price_value_line = get_next_line(
            lines,
            r"Ticket Price"
        )

        if price_value_line:
            price_match = re.search(
                r"(?:Rs\.?|₹)\s*[\d,]+(?:\.\d{1,2})?",
                price_value_line["text"],
                re.IGNORECASE
            )

            if price_match:
                fields["ticket_price"] = create_field(
                    price_match.group(0), price_value_line
                )

        # Seat number
        seat_line = get_next_line(
            lines,
            r"^\s*Seat no\s*$"
        )

        if seat_line:
            seat_value = seat_line["text"].strip().upper()

            # Accept seat identifiers, not passenger names
            if re.fullmatch(r"[A-Z0-9-]{1,10}", seat_value):
                fields["seat"] = create_field(
                    seat_value, seat_line
                )

    # Arrival date and time
    arrival_line = get_next_line(
        lines,
        r"DROPPING DATE\s*&\s*TIME"
    )

    if arrival_line:
        match = re.search(
            r"(\d{1,2}/\d{1,2}/\d{4}),?\s*(\d{1,2}:\d{2}\s*[AP]M)?",
            arrival_line["text"],
            re.IGNORECASE
        )

        if match:
            fields["arrival_date"] = create_field(
                match.group(1), arrival_line
            )

            if match.group(2):
                fields["arrival_time"] = create_field(
                    match.group(2), arrival_line
                )

    return make_ticket(
        "bus",
        "redBus",
        fields
    )

def extract_ticket(ocr_result):
    """
    Extract ticket information using issuer-specific
    and generic extraction, then merge their results.
    """

    lines = ocr_result.get("lines", [])

    full_text = "\n".join(
        line.get("text", "") for line in lines
    )

    document_type = detect_document_type(full_text)

    # Step 1: Issuer-specific extraction
    ticket = None

    if document_type == "flight":
        ticket = extract_flight(lines)

    elif document_type == "train":
        ticket = extract_train(lines)

    elif document_type == "bus":
        ticket = extract_bus(lines)

    # Step 2: Generic extraction
    generic_result = extract_generic_fields(lines)

    # Step 3: Create a generic ticket if issuer extraction fails
    if ticket is None:
        ticket = make_ticket(
            document_type or "unknown",
            "Unknown",
            {},
            observations={}
        )

    # Step 4: Merge both extraction results
    specific_fields = ticket.get("fields", {})

    merge_result = merge_fields(
        specific_fields,
        generic_result["fields"]
    )

    # Step 5: Update final extracted fields
    ticket["fields"] = merge_result["fields"]

    # Step 5.1: Collect repeated OCR observations
    repeated_result = collect_repeated_observations(
        lines,
        ticket["fields"]
    )

    # Step 6: Preserve merger evidence
    ticket.setdefault("observations", {})

    ticket["observations"]["generic_ambiguities"] = (
        generic_result.get("ambiguous_fields", {})
    )

    ticket["observations"]["field_comparisons"] = (
        merge_result["comparisons"]
    )

    ticket["observations"]["field_conflicts"] = (
        merge_result["conflicts"]
    )

    ticket["observations"]["field_validations"] = (
        merge_result["validations"]
    )

    ticket["observations"]["repeated_fields"] = (
    repeated_result["repeated_observations"]
    )

    ticket["observations"]["observation_count"] = (
        repeated_result["observation_count"]
    )

    return ticket

