import re

from .ticket_schema import make_field, make_document_record
from app.authenticity.generic_extractor import extract_generic_fields, is_label_line
from app.authenticity.field_merger import merge_fields
from app.authenticity.observation_collector import (
    collect_repeated_observations
)
from app.authenticity.bus_field_filter import (
    filter_bus_generic_fields,
)

KNOWN_AIRLINES = [
    "IndiGo", "Air India", "Emirates", "Delta", "United Airlines", "United",
    "American Airlines", "British Airways", "Lufthansa", "Qatar Airways",
    "Singapore Airlines", "Air France", "KLM", "Virgin Atlantic", "Qantas",
    "Etihad Airways", "Etihad", "Vistara", "SpiceJet", "Akasa Air",
    "Southwest", "Ryanair", "easyJet", "AirAsia", "Turkish Airlines",
    "Cathay Pacific", "JetBlue", "Alaska Airlines"
]

KNOWN_RAIL_OPERATORS = [
    "IRCTC", "Indian Railways", "Amtrak", "Eurostar", "Deutsche Bahn",
    "DB", "SNCF", "Renfe", "Trenitalia", "National Rail", "SBB", "ÖBB",
    "Via Rail", "Japan Railways", "JR"
]

KNOWN_BUS_PLATFORMS = [
    "redBus", "FlixBus", "Greyhound", "Megabus", "National Express",
    "Abhibus", "Stagecoach", "Eurolines"
]


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
    """
    Classify documents using weighted combinations of indicators.

    Strong document-specific indicators receive higher scores.
    Weak or ambiguous keywords cannot independently determine
    the document category.
    """
    text_lower = text.lower()

    def contains(phrase):
        pattern = (
            r"(?<![a-z0-9])"
            + re.escape(phrase.lower())
            + r"(?![a-z0-9])"
        )
        return bool(re.search(pattern, text_lower))

    scores = {
        "flight": 0,
        "train": 0,
        "bus": 0,
        "invoice": 0,
        "receipt": 0,
        "bank_statement": 0,
        "certificate": 0,
    }

    # ---------------- FLIGHT ----------------

    for phrase in [
        "boarding pass",
        "e-ticket itinerary",
        "airline booking reference",
    ]:
        if contains(phrase):
            scores["flight"] += 5

    if contains("flight number") or contains("flight no"):
        scores["flight"] += 3

    if contains("departure airport") and contains("arrival airport"):
        scores["flight"] += 4

    if (
        contains("flight")
        and any(contains(a) for a in KNOWN_AIRLINES)
    ):
        scores["flight"] += 2

    # ---------------- TRAIN ----------------

    if contains("electronic reservation slip"):
        scores["train"] += 6

    if contains("indian railways"):
        scores["train"] += 5

    if contains("irctc"):
        scores["train"] += 4

    if contains("train number") or contains("train no"):
        scores["train"] += 3

    if contains("coach") and contains("berth"):
        scores["train"] += 3

    # PNR alone is not sufficient evidence of a train ticket.
    if contains("pnr"):
        scores["train"] += 1

    if contains("train") and contains("journey date"):
        scores["train"] += 2

    # ---------------- BUS ----------------

    if contains("bus ticket") or contains("bus booking"):
        scores["bus"] += 5

    if contains("bus operator"):
        scores["bus"] += 3

    if contains("boarding point") and contains("dropping point"):
        scores["bus"] += 4

    if any(contains(b) for b in KNOWN_BUS_PLATFORMS):
        scores["bus"] += 2

    # ---------------- BANK STATEMENT ----------------

    if contains("bank statement"):
        scores["bank_statement"] += 6

    if contains("account statement"):
        scores["bank_statement"] += 5

    if contains("statement of account"):
        scores["bank_statement"] += 5

    if contains("opening balance") and contains("closing balance"):
        scores["bank_statement"] += 3

    # ---------------- CERTIFICATE ----------------

    for phrase in [
        "this is to certify",
        "certifies that",
        "awarded to",
        "certificate of",
        "completion certificate",
        "degree certificate",
    ]:
        if contains(phrase):
            scores["certificate"] += 5

    # ---------------- INVOICE ----------------

    if contains("tax invoice") or contains("commercial invoice"):
        scores["invoice"] += 6

    if contains("proforma invoice") or contains("bill of supply"):
        scores["invoice"] += 5

    if contains("invoice number") or contains("invoice no"):
        scores["invoice"] += 2

    if contains("invoice date"):
        scores["invoice"] += 2

    if contains("gstin") and contains("subtotal"):
        scores["invoice"] += 4

    # ---------------- RECEIPT ----------------

    if contains("payment receipt"):
        scores["receipt"] += 6

    if contains("cash memo") or contains("sales receipt"):
        scores["receipt"] += 5

    if contains("payment confirmation"):
        scores["receipt"] += 4

    if contains("receipt number") or contains("receipt no"):
        scores["receipt"] += 2

    if contains("paid amount") and contains("transaction date"):
        scores["receipt"] += 3

    # ---------------- FINAL CLASSIFICATION ----------------

    ranked = sorted(
        scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    best_type, best_score = ranked[0]
    second_score = ranked[1][1]

    # Require meaningful evidence and a clear distinction
    # from the next most likely document category.
    if best_score < 4:
        return "generic"

    if best_score - second_score < 2:
        return "generic"

    return best_type

def detect_issuer(text: str, document_type: str) -> str | None:
    """
    Dynamically identify the issuer / vendor / provider from text,
    avoiding hardcoded assumptions.
    """
    if document_type == "flight":
        for airline in KNOWN_AIRLINES:
            if re.search(r"\b" + re.escape(airline) + r"\b", text, re.IGNORECASE):
                return airline
        return None

    elif document_type == "train":
        for operator in KNOWN_RAIL_OPERATORS:
            if re.search(r"\b" + re.escape(operator) + r"\b", text, re.IGNORECASE):
                return operator
        return None

    elif document_type == "bus":
        for platform in KNOWN_BUS_PLATFORMS:
            if re.search(r"\b" + re.escape(platform) + r"\b", text, re.IGNORECASE):
                return platform
        m = re.search(r"([A-Za-z0-9\s]{3,30})\s+(?:Travels|Transport|Lines|Express|Roadways)", text)
        if m:
            return m.group(0).strip()
        return None

    elif document_type == "invoice":
        # Look for company name near top
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:4]:
            if not is_label_line(line) and not re.search(r"(?i)\b(invoice|tax|date|page|bill to)\b", line):
                if len(line) >= 3 and len(line) <= 40:
                    return line
        return None

    elif document_type == "receipt":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:3]:
            if not is_label_line(line) and not re.search(r"(?i)\b(receipt|date|cash|total)\b", line):
                if len(line) >= 3 and len(line) <= 40:
                    return line
        return None

    elif document_type == "bank_statement":
        m = re.search(r"([A-Za-z\s]{3,30}\bBank\b|[A-Za-z\s]{3,30}\bBanking\b)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return None

    return None


def extract_flight(lines):
    """Generalized flight ticket / boarding pass extraction for any airline."""
    fields = {}
    full_text = "\n".join(l.get("text", "") for l in lines)
    issuer = detect_issuer(full_text, "flight")

    # Flight number
    flight_line = get_line(
        lines,
        r"^\s*[A-Z0-9]{2}\s*\d{3,4}[A-Z]?\s*$"
    )
    if not flight_line:
        flight_line = get_line(lines, r"\b[A-Z0-9]{2}\s*\d{3,4}[A-Z]?\b")

    # Route: "ORIGIN (XXX) To DESTINATION (YYY)" or "ORIGIN To DESTINATION"
    route_line = get_line(
        lines,
        r"\b[A-Z][A-Z\s]+\s*(?:\([^)]*\))?\s*To\s*[A-Z][A-Z\s]+"
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

    if flight_line:
        m = re.search(r"[A-Z0-9]{2}\s*\d{3,4}[A-Z]?", flight_line["text"])
        fields["flight_number"] = create_field(
            m.group(0) if m else flight_line["text"], flight_line
        )

    # Date
    date_line = get_line(lines, r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b")
    if date_line:
        match = re.search(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b", date_line["text"])
        fields["departure_date"] = create_field(match.group(0), date_line)

    # Boarding time
    boarding_line = get_line(lines, r"\b\d{1,2}:\d{2}\s*hrs?\b|\bBoarding\s+Time\b")
    if boarding_line:
        match = re.search(r"\d{1,2}:\d{2}", boarding_line["text"])
        if match:
            fields["boarding_time"] = create_field(match.group(0), boarding_line)
        else:
            next_l = get_next_line(lines, r"\bBoarding\s+Time\b")
            if next_l:
                m2 = re.search(r"\d{1,2}:\d{2}", next_l["text"])
                if m2:
                    fields["boarding_time"] = create_field(m2.group(0), next_l)

    # Departure time
    departure_line = get_line(lines, r"\bDeparture\s*(?:Time)?\s*[:\-]?\s*\d{1,2}:\d{2}")
    if departure_line:
        match = re.search(r"\d{1,2}:\d{2}", departure_line["text"])
        if match:
            fields["departure_time"] = create_field(match.group(0), departure_line)

    # Seat extraction
    seat_label_index = None
    for index, line in enumerate(lines):
        if re.search(r"\bSeat\b", line.get("text", ""), re.IGNORECASE):
            seat_label_index = index
            break

    if seat_label_index is not None:
        start = max(0, seat_label_index - 1)
        end = min(len(lines), seat_label_index + 7)
        seat_pattern = re.compile(
            r"^\s*(?:Seat\s*[:\-]?\s*)?([1-9]|[1-5]\d|60)([A-F])\s*$",
            re.IGNORECASE
        )
        for candidate in lines[start:end]:
            match = seat_pattern.fullmatch(candidate.get("text", ""))
            if match:
                fields["seat"] = create_field(
                    match.group(1) + match.group(2).upper(),
                    candidate
                )
                break

    # Passenger name
    passenger_line = get_line(lines, r"\b[A-Z]+/[A-Z\s]+/(?:MR|MRS|MS)\b")
    if passenger_line:
        fields["passenger_name"] = create_field(
            passenger_line["text"], passenger_line
        )

        # PNR / Airline booking reference
    pnr_line = get_line(
        lines,
        r"^\s*PNR\s*[:\-]?\s*[A-Z0-9]{5,10}\s*$"
    )

    if pnr_line:
        match = re.search(
            r"\bPNR\s*[:\-]?\s*([A-Z0-9]{5,10})\b",
            pnr_line["text"],
            re.IGNORECASE
        )
        if match:
            fields["pnr"] = create_field(
                match.group(1).upper(),
                pnr_line
            )
    else:
        pnr_value_line = get_next_line(
            lines,
            r"^\s*PNR\s*[:\-]?\s*$"
        )

        if pnr_value_line:
            pnr_value = pnr_value_line["text"].strip()

            if re.fullmatch(r"[A-Z0-9]{5,10}", pnr_value, re.IGNORECASE):
                fields["pnr"] = create_field(
                    pnr_value.upper(),
                    pnr_value_line
                )

    return make_document_record(
        document_type="flight",
        issuer=issuer,
        fields=fields,
        category="transport"
    )


def extract_train(lines):
    """Generalized train ticket extraction for any rail operator."""
    fields = {}
    full_text = "\n".join(l.get("text", "") for l in lines)
    issuer = detect_issuer(full_text, "train")

    def extract_station(label_pattern):
        for line in lines:
            text = line.get("text", "").strip()
            if not re.search(label_pattern, text, re.IGNORECASE):
                continue

            inline_match = re.search(
                rf"(?:{label_pattern})\s*[:*-]?\s*(.+)$",
                text,
                re.IGNORECASE
            )
            if inline_match and inline_match.group(1):
                value = inline_match.group(1).strip()
                if value and not re.fullmatch(
                    r"Boarding At|To|From|Journey Date",
                    value,
                    re.IGNORECASE
                ):
                    return create_field(value, line)

            from app.authenticity.spatial_matching import match_spatial_value
            spatial_result = match_spatial_value(line, lines)
            if spatial_result.get("status") == "matched":
                candidate = spatial_result.get("candidate", {})
                candidate_text = candidate.get("text", "").strip()
                if candidate_text and not re.fullmatch(
                    r"Boarding At|To|From|Journey Date",
                    candidate_text,
                    re.IGNORECASE
                ):
                    return create_field(candidate_text, candidate)

        return None

    # Train number and name
    train_line = get_line(lines, r"\b\d{4,5}\s*/\s*[A-Z][A-Z0-9\s]+")
    if train_line:
        match = re.search(r"\b(\d{4,5})\s*/\s*(.+)", train_line["text"])
        if match:
            fields["train_number"] = create_field(match.group(1), train_line)
            fields["train_name"] = create_field(match.group(2).strip(), train_line)

    origin = extract_station(
        r"^\s*Booked\s+from\b|^\s*Boarding At\b|^\s*From\b"
    )
    if origin:
        fields["origin"] = origin

    destination = extract_station(r"^\s*To\b|^\s*Destination\b")
    if destination:
        fields["destination"] = destination

    # Journey date
    date_line = get_line(lines, r"(?:Start Date|Journey Date)\s*\*?\s*\d{1,2}[-/]\w+[-/]\d{4}")
    if date_line:
        match = re.search(r"\d{1,2}[-/]\w+[-/]\d{4}", date_line["text"])
        if match:
            fields["journey_date"] = create_field(match.group(0), date_line)

    departure_line = get_line(lines, r"Departure\s*\*?\s*\d{1,2}:\d{2}")
    if departure_line:
        match = re.search(r"Departure\s*\*?\s*(\d{1,2}:\d{2})", departure_line["text"], re.IGNORECASE)
        if match:
            fields["departure_time"] = create_field(match.group(1), departure_line)

    arrival_line = get_line(lines, r"Arrival\s*\*?\s*\d{1,2}:\d{2}")
    if arrival_line:
        match = re.search(r"Arrival\s*\*?\s*(\d{1,2}:\d{2})", arrival_line["text"], re.IGNORECASE)
        if match:
            fields["arrival_time"] = create_field(match.group(1), arrival_line)

        date_match = re.search(r"\d{1,2}:\d{2}\s+(\d{1,2}[-/]\w+[-/]\d{4})", arrival_line["text"])
        if date_match:
            fields["arrival_date"] = create_field(date_match.group(1), arrival_line)

    class_line = get_line(lines, r"SECOND AC|FIRST AC|THIRD AC|SLEEPER|CHAIR CAR|EXECUTIVE")
    if class_line:
        fields["travel_class"] = create_field(class_line["text"], class_line)

    return make_document_record(
        document_type="train",
        issuer=issuer,
        fields=fields,
        category="transport"
    )



def extract_bus(lines):
    """Extract fields from bus tickets using bus-specific section scanning."""
    fields = {}
    full_text = "\n".join(line.get("text", "") for line in lines)
    issuer = detect_issuer(full_text, "bus")

    def text_at(index):
        if 0 <= index < len(lines):
            return str(lines[index].get("text", "")).strip()
        return ""

    def add_field(key, value, index):
        value = str(value).strip()
        if value and index < len(lines):
            fields[key] = create_field(value, lines[index])

    def find_label(pattern, start=0):
        for i in range(start, len(lines)):
            if re.search(pattern, text_at(i), re.IGNORECASE):
                return i
        return None

    def next_meaningful(start, limit=5, stop_pattern=None):
        for i in range(start + 1, min(len(lines), start + limit + 1)):
            value = text_at(i)

            if not value:
                continue

            if stop_pattern and re.search(stop_pattern, value, re.IGNORECASE):
                break

            # Skip OCR decorative symbols such as 日 and 黃.
            if not re.search(r"[A-Za-z0-9]", value):
                continue

            return i

        return None

    def extract_datetime(label_pattern, field_date, field_time):
        index = find_label(label_pattern)
        if index is None:
            return

        for i in range(index + 1, min(len(lines), index + 7)):
            value = text_at(i)

            match = re.search(
                r"(\d{1,2}/\d{1,2}/\d{4})"
                r"(?:,?\s*(\d{1,2}:\d{2}\s*[AP]M))?",
                value,
                re.IGNORECASE
            )

            if match:
                add_field(field_date, match.group(1), i)

                if match.group(2):
                    add_field(field_time, match.group(2), i)

                return

    # Ticket number: supports inline and next-line values.
    ticket_index = find_label(r"Ticket\s+Number")

    if ticket_index is not None:
        ticket_text = text_at(ticket_index)

        match = re.search(
            r"Ticket\s+Number\s*[:#]?\s*([A-Z0-9-]+)",
            ticket_text,
            re.IGNORECASE
        )

        if match:
            add_field("ticket_number", match.group(1), ticket_index)
        else:
            value_index = next_meaningful(ticket_index, limit=2)
            if value_index is not None:
                add_field("ticket_number", text_at(value_index), value_index)

    # PNR: supports inline and next-line values.
    pnr_index = find_label(r"\bPNR(?:\s+No)?\b")

    if pnr_index is not None:
        pnr_text = text_at(pnr_index)

        match = re.search(
            r"\bPNR(?:\s+No)?\.?\s*[:#]?\s*([A-Z0-9-]+)",
            pnr_text,
            re.IGNORECASE
        )

        if match:
            add_field("pnr", match.group(1), pnr_index)
        else:
            value_index = next_meaningful(pnr_index, limit=2)
            if value_index is not None:
                add_field("pnr", text_at(value_index), value_index)

    # Journey date and departure time.
    extract_datetime(
        r"Journey Date and Time|Journey Date",
        "journey_date",
        "departure_time"
    )

    # Arrival date and time.
    extract_datetime(
        r"DROPPING DATE\s*&\s*TIME|Arrival Time",
        "arrival_date",
        "arrival_time"
    )

    # Boarding and dropping sections.
    boarding_index = find_label(r"^\s*Boarding Point\s*$")
    dropping_index = find_label(r"^\s*Dropping Point\s*$")

    if boarding_index is not None:
        end = dropping_index if dropping_index is not None else min(
            len(lines), boarding_index + 7
        )

        candidates = []
        for i in range(boarding_index + 1, end):
            value = text_at(i)
            if value and re.search(r"[A-Za-z]", value):
                if not re.search(
                    r"Landmark|Contact|Phone|Passenger|Ticket|Date",
                    value,
                    re.IGNORECASE
                ):
                    candidates.append((i, value))

        if candidates:
            add_field("origin", candidates[0][1], candidates[0][0])

            if len(candidates) > 1:
                add_field(
                    "boarding_point",
                    candidates[1][1],
                    candidates[1][0]
                )

    if dropping_index is not None:
        end = find_label(
            r"DROPPING DATE\s*&\s*TIME|Passenger Details",
            start=dropping_index + 1
        )
        if end is None:
            end = min(len(lines), dropping_index + 7)

        candidates = []
        for i in range(dropping_index + 1, end):
            value = text_at(i)
            if value and re.search(r"[A-Za-z]", value):
                if not re.search(
                    r"Landmark|Contact|Phone|Date|Time",
                    value,
                    re.IGNORECASE
                ):
                    candidates.append((i, value))

        if candidates:
            add_field("destination", candidates[0][1], candidates[0][0])

            if len(candidates) > 1:
                add_field(
                    "dropping_point",
                    candidates[1][1],
                    candidates[1][0]
                )

    # Operator: skip decorative OCR lines after Travels.
    operator_index = find_label(r"^\s*(?:Travels|Bus Operator)\s*$")
    if operator_index is not None:
        value_index = next_meaningful(operator_index, limit=3)

        if value_index is not None:
            operator_value = text_at(value_index)

            if not re.search(
                r"Ticket|Journey|Boarding|Dropping|Passenger|Price",
                operator_value,
                re.IGNORECASE
            ):
                add_field("operator", operator_value, value_index)

                # Travel class is often immediately after the operator.
                class_index = next_meaningful(value_index, limit=3)

                if class_index is not None:
                    class_value = text_at(class_index)

                    if re.search(
                        r"A/C|AC|Sleeper|Seater|Non.?AC",
                        class_value,
                        re.IGNORECASE
                    ):
                        add_field(
                            "travel_class",
                            class_value,
                            class_index
                        )

    # Ticket price.
    for i, line in enumerate(lines):
        if re.search(r"Ticket Price|Total Fare", text_at(i), re.IGNORECASE):
            match = re.search(
                r"(?:Rs\.?|INR|₹|\$|€)\s*[\d,]+(?:\.\d{1,2})?",
                text_at(i),
                re.IGNORECASE
            )

            if match:
                add_field("ticket_price", match.group(0), i)
                break

            value_index = next_meaningful(i, limit=3)
            if value_index is not None:
                match = re.search(
                    r"(?:Rs\.?|INR|₹|\$|€)\s*[\d,]+(?:\.\d{1,2})?",
                    text_at(value_index),
                    re.IGNORECASE
                )
                if match:
                    add_field("ticket_price", match.group(0), value_index)
                    break

    # Passenger name and seat, using the Passenger Details section.
    passenger_index = find_label(r"^\s*Passenger Details\s*$")

    if passenger_index is not None:
        seat_label = find_label(
            r"^\s*Seat\s+no\s*$|^\s*Seat\s*$",
            start=passenger_index + 1
        )

        if seat_label is not None:
            section_end = min(len(lines), seat_label + 8)
            passenger_candidates = []

            for i in range(seat_label + 1, section_end):
                value = text_at(i)

                if not value:
                    continue

                # Ignore numeric passenger count and age/gender details.
                if re.fullmatch(r"\d+", value):
                    continue

                if re.search(
                    r"Yrs|Years|Male|Female|Gender|Passenger|Contact",
                    value,
                    re.IGNORECASE
                ):
                    continue

                if re.fullmatch(r"[A-Za-z][A-Za-z .'-]{2,}", value):
                    passenger_candidates.append((i, value))

            if passenger_candidates:
                name_index, name_value = passenger_candidates[0]
                add_field("passenger_name", name_value, name_index)

                # Prefer the seat identifier immediately after the name.
                for i in range(name_index + 1, section_end):
                    value = text_at(i).upper()

                    if re.fullmatch(r"[A-Z]{1,3}\d{1,3}", value):
                        add_field("seat", value, i)
                        break

    return make_document_record(
        document_type="bus",
        issuer=issuer,
        fields=fields,
        category="transport"
    )

def extract_invoice(lines):
    """Extraction template for commercial invoices."""
    fields = {}
    full_text = "\n".join(l.get("text", "") for l in lines)
    issuer = detect_issuer(full_text, "invoice")

    inv_line = get_line(lines, r"\b(?:invoice\s*no\.?|invoice\s*number|invoice\s*#|inv\s*no\.?|inv\s*#|bill\s*no\.?|bill\s*number)\b\s*[:\-]?\s*([A-Za-z0-9\-/_#]+)")
    if not inv_line:
        inv_line = get_line(lines, r"\b(?:invoice|inv|bill)\b\s*[:\-]\s*([A-Za-z0-9\-/_#]+)")

    if inv_line:
        m = re.search(
            r"\b(?:invoice\s*no\.?|invoice\s*number|invoice\s*#|inv\s*no\.?|inv\s*#|bill\s*no\.?|bill\s*number)\b\s*[:\-]?\s*([A-Za-z0-9\-/_#]+)",
            inv_line["text"],
            re.IGNORECASE
        )
        if not m:
            m = re.search(r"\b(?:invoice|inv|bill)\b\s*[:\-]\s*([A-Za-z0-9\-/_#]+)", inv_line["text"], re.IGNORECASE)
        if m:
            fields["invoice_number"] = create_field(m.group(1).strip(), inv_line)

    date_line = get_line(lines, r"\b(?:invoice\s*date|bill\s*date|issue\s*date|date\s*of\s*invoice)\b")
    if date_line:
        m = re.search(r"\b(\d{1,2}[-/]\w+[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b", date_line["text"])
        if m:
            fields["invoice_date"] = create_field(m.group(1).strip(), date_line)

    due_line = get_line(lines, r"\b(?:due\s*date|pay\s*by|payment\s*due)\b")
    if due_line:
        m = re.search(r"\b(\d{1,2}[-/]\w+[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b", due_line["text"])
        if m:
            fields["due_date"] = create_field(m.group(1).strip(), due_line)

    total_line = get_line(lines, r"\b(?:grand\s*total|total\s*amount|total\s*due|amount\s*payable|net\s*payable)\b")
    if total_line:
        m = re.search(r"(?:[₹$€£]\s*)?[\d,]+(?:\.\d{1,2})?", total_line["text"])
        if m:
            fields["total_amount"] = create_field(m.group(0).strip(), total_line)

    sub_line = get_line(lines, r"\b(?:sub\s*total|subtotal|taxable\s*amount)\b")
    if sub_line:
        m = re.search(r"(?:[₹$€£]\s*)?[\d,]+(?:\.\d{1,2})?", sub_line["text"])
        if m:
            fields["subtotal"] = create_field(m.group(0).strip(), sub_line)

    tax_line = get_line(lines, r"\b(?:total\s*tax|tax\s*amount|gst|vat)\b")
    if tax_line:
        m = re.search(r"(?:[₹$€£]\s*)?[\d,]+(?:\.\d{1,2})?", tax_line["text"])
        if m:
            fields["tax_amount"] = create_field(m.group(0).strip(), tax_line)

    cust_line = get_line(lines, r"\b(?:bill\s*to|billed\s*to|customer|client)\s*[:\-]?\s*(.+)")
    if cust_line:
        m = re.search(r"\b(?:bill\s*to|billed\s*to|customer|client)\s*[:\-]?\s*(.+)", cust_line["text"], re.IGNORECASE)
        if m and m.group(1).strip():
            fields["customer_name"] = create_field(m.group(1).strip(), cust_line)

    return make_document_record(
        document_type="invoice",
        issuer=issuer,
        fields=fields,
        category="commercial"
    )


def extract_receipt(lines):
    """Extraction template for receipts and payment vouchers."""
    fields = {}
    full_text = "\n".join(l.get("text", "") for l in lines)
    issuer = detect_issuer(full_text, "receipt")

    rec_line = get_line(lines, r"\b(?:receipt|rec|ref|voucher)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Za-z0-9\-/_#]+)")
    if rec_line:
        m = re.search(r"\b(?:receipt|rec|ref|voucher)\s*(?:no\.?|number|#)?\s*[:\-]?\s*([A-Za-z0-9\-/_#]+)", rec_line["text"], re.IGNORECASE)
        if m:
            fields["receipt_number"] = create_field(m.group(1).strip(), rec_line)

    date_line = get_line(lines, r"\b(?:date|receipt\s*date|paid\s*date)\b")
    if date_line:
        m = re.search(r"\b(\d{1,2}[-/]\w+[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b", date_line["text"])
        if m:
            fields["receipt_date"] = create_field(m.group(1).strip(), date_line)

    total_line = get_line(lines, r"\b(?:total|amount\s*paid|paid|net\s*amount)\b")
    if total_line:
        m = re.search(r"(?:[₹$€£]\s*)?[\d,]+(?:\.\d{1,2})?", total_line["text"])
        if m:
            fields["total_amount"] = create_field(m.group(0).strip(), total_line)

    return make_document_record(
        document_type="receipt",
        issuer=issuer,
        fields=fields,
        category="commercial"
    )


def extract_bank_statement(lines):
    """Extraction template for bank statements."""
    fields = {}
    full_text = "\n".join(l.get("text", "") for l in lines)
    issuer = detect_issuer(full_text, "bank_statement")

    acct_line = get_line(lines, r"\b(?:account|a/c|acct)\s*(?:no\.?|number)?\s*[:\-]?\s*([\dX\*\-]{6,26})")
    if acct_line:
        m = re.search(r"\b(?:account|a/c|acct)\s*(?:no\.?|number)?\s*[:\-]?\s*([\dX\*\-]{6,26})", acct_line["text"], re.IGNORECASE)
        if m:
            fields["account_number"] = create_field(m.group(1).strip(), acct_line)

    date_line = get_line(lines, r"\b(?:statement\s*date|date)\b")
    if date_line:
        m = re.search(r"\b(\d{1,2}[-/]\w+[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b", date_line["text"])
        if m:
            fields["statement_date"] = create_field(m.group(1).strip(), date_line)

    return make_document_record(
        document_type="bank_statement",
        issuer=issuer,
        fields=fields,
        category="financial"
    )


def extract_certificate(lines):
    """Extraction template for certificates."""
    fields = {}
    full_text = "\n".join(l.get("text", "") for l in lines)
    issuer = detect_issuer(full_text, "certificate")

    date_line = get_line(lines, r"\b(?:issue\s*date|dated|date)\b")
    if date_line:
        m = re.search(r"\b(\d{1,2}[-/]\w+[-/]\d{2,4}|\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4})\b", date_line["text"])
        if m:
            fields["issue_date"] = create_field(m.group(1).strip(), date_line)

    cert_id_line = get_line(lines, r"\b(?:certificate\s*id|cert\s*no|credential\s*id)\s*[:\-]?\s*([A-Za-z0-9\-/_]+)")
    if cert_id_line:
        m = re.search(r"\b(?:certificate\s*id|cert\s*no|credential\s*id)\s*[:\-]?\s*([A-Za-z0-9\-/_]+)", cert_id_line["text"], re.IGNORECASE)
        if m:
            fields["certificate_id"] = create_field(m.group(1).strip(), cert_id_line)

    return make_document_record(
        document_type="certificate",
        issuer=issuer,
        fields=fields,
        category="official"
    )


def extract_document(ocr_result):
    """
    Generalized schema-driven document extraction pipeline:
    1. Classifies document type (flight, train, bus, invoice, receipt, statement, certificate, generic)
    2. Applies type-specific schema extractor
    3. Runs generic spatial and alias-based extraction
    4. Merges specific and generic results cleanly
    5. Collects repeated observations for consistency review
    """
    lines = ocr_result.get("lines", [])
    full_text = "\n".join(line.get("text", "") for line in lines)

    document_type = detect_document_type(full_text)

    # Step 1: Type-specific extraction
    doc_record = None

    if document_type == "flight":
        doc_record = extract_flight(lines)
    elif document_type == "train":
        doc_record = extract_train(lines)
    elif document_type == "bus":
        doc_record = extract_bus(lines)
    elif document_type == "invoice":
        doc_record = extract_invoice(lines)
    elif document_type == "receipt":
        doc_record = extract_receipt(lines)
    elif document_type == "bank_statement":
        doc_record = extract_bank_statement(lines)
    elif document_type == "certificate":
        doc_record = extract_certificate(lines)

    # Step 2: Generic extraction
    generic_result = extract_generic_fields(lines)

    # Apply bus-specific filtering only.
    # Flight and train extraction remain unchanged.
    if document_type == "bus":
        generic_result["fields"] = filter_bus_generic_fields(
            generic_result.get("fields", {}),
            doc_record.get("fields", {}) if doc_record else {}
        )

    # Step 3: Fallback generic document record if specific extraction yielded None
    if doc_record is None:
        issuer = detect_issuer(full_text, document_type or "generic")
        doc_record = make_document_record(
            document_type=document_type or "generic",
            issuer=issuer,
            fields={},
            observations={}
        )

    # Step 4: Merge specific and generic fields
    specific_fields = doc_record.get("fields", {})
    merge_result = merge_fields(
        specific_fields,
        generic_result.get("fields", {})
    )

    doc_record["fields"] = merge_result["fields"]

    # An explicitly labelled issuer also supports providers outside the known
    # operator lists. Missing evidence stays unknown rather than a placeholder.
    issuer_field = doc_record["fields"].get("issuer")
    if issuer_field and issuer_field.get("value"):
        doc_record["issuer"] = issuer_field["value"]

    # Step 5: Collect repeated OCR observations for consistency review
    repeated_result = collect_repeated_observations(
        lines,
        doc_record["fields"]
    )

    # Step 6: Preserve merger evidence
    doc_record.setdefault("observations", {})
    doc_record["observations"]["generic_ambiguities"] = generic_result.get("ambiguous_fields", {})
    doc_record["observations"]["field_comparisons"] = merge_result.get("comparisons", {})
    doc_record["observations"]["field_conflicts"] = merge_result.get("conflicts", {})
    doc_record["observations"]["field_validations"] = merge_result.get("validations", {})
    doc_record["observations"]["repeated_fields"] = repeated_result.get("repeated_observations", {})
    doc_record["observations"]["observation_count"] = repeated_result.get("observation_count", 0)

    return doc_record


# Backward compatibility alias
def extract_ticket(ocr_result):
    return extract_document(ocr_result)
