import re

from .ticket_schema import make_field, make_document_record, make_ticket
from app.authenticity.generic_extractor import extract_generic_fields
from app.authenticity.field_merger import merge_fields
from app.authenticity.observation_collector import (
    collect_repeated_observations
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
    Generalized schema-driven document type classification.
    Supports commercial invoices, payment receipts, bank statements,
    certificates, flight boarding passes, train tickets, bus tickets,
    and generic documents.
    """
    text_lower = text.lower()

    # 1. Commercial Invoice
    if any(k in text_lower for k in [
        "tax invoice", "commercial invoice", "bill of supply",
        "proforma invoice", "invoice no", "invoice #", "inv no",
        "invoice date", "gstin", "subtotal"
    ]) and ("ticket" not in text_lower or "invoice" in text_lower):
        return "invoice"

    # 2. Payment Receipt / Cash Memo
    if any(k in text_lower for k in [
        "payment receipt", "cash memo", "sales receipt",
        "receipt no", "receipt #", "paid amount", "payment confirmation"
    ]):
        return "receipt"

    # 3. Bank / Account Statement
    if any(k in text_lower for k in [
        "bank statement", "account statement", "statement of account",
        "opening balance", "closing balance", "statement period"
    ]):
        return "bank_statement"

    # 4. Certificate / Credential
    if any(k in text_lower for k in [
        "this is to certify", "certifies that", "awarded to",
        "certificate of", "completion certificate", "degree certificate"
    ]):
        return "certificate"

    # 5. Flight Ticket / Boarding Pass (Any Airline)
    if any(k in text_lower for k in [
        "boarding pass", "flight number", "flight no", "boarding time",
        "gate", "terminal"
    ]) or ("flight" in text_lower and any(a.lower() in text_lower for a in KNOWN_AIRLINES)):
        return "flight"

    # 6. Train Ticket (Any Rail Operator)
    if any(k in text_lower for k in [
        "electronic reservation slip", "irctc", "railway", "railways",
        "train no", "train number", "berth", "coach"
    ]) or ("train" in text_lower and any(r.lower() in text_lower for r in KNOWN_RAIL_OPERATORS)):
        return "train"

    # 7. Bus Ticket (Any Bus Operator)
    if any(k in text_lower for k in [
        "bus ticket", "ticket information", "boarding point",
        "dropping point"
    ]) or ("bus" in text_lower and any(b.lower() in text_lower for b in KNOWN_BUS_PLATFORMS)):
        return "bus"

    # Fallback to travel types if keywords exist
    if "boarding pass" in text_lower or "flight" in text_lower:
        return "flight"
    if "train" in text_lower or "rail" in text_lower or "ers" in text_lower:
        return "train"
    if "bus" in text_lower:
        return "bus"

    return "generic"


def detect_issuer(text: str, document_type: str) -> str:
    """
    Dynamically identify the issuer / vendor / provider from text,
    avoiding hardcoded assumptions.
    """
    text_lower = text.lower()

    if document_type == "flight":
        for airline in KNOWN_AIRLINES:
            if re.search(r"\b" + re.escape(airline) + r"\b", text, re.IGNORECASE):
                return airline
        return "Aviation Carrier"

    elif document_type == "train":
        for operator in KNOWN_RAIL_OPERATORS:
            if re.search(r"\b" + re.escape(operator) + r"\b", text, re.IGNORECASE):
                return operator
        if "electronic reservation slip" in text.lower() or "ers" in text.lower():
            return "IRCTC"
        return "Rail Operator"

    elif document_type == "bus":
        for platform in KNOWN_BUS_PLATFORMS:
            if re.search(r"\b" + re.escape(platform) + r"\b", text, re.IGNORECASE):
                return platform
        m = re.search(r"([A-Za-z0-9\s]{3,30})\s+(?:Travels|Transport|Lines|Express|Roadways)", text)
        if m:
            return m.group(0).strip()
        return "Bus Operator"

    elif document_type == "invoice":
        # Look for company name near top
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:4]:
            if not re.search(r"(?i)\b(invoice|tax|date|page|bill to)\b", line):
                if len(line) >= 3 and len(line) <= 40:
                    return line
        return "Commercial Vendor"

    elif document_type == "receipt":
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:3]:
            if not re.search(r"(?i)\b(receipt|date|cash|total)\b", line):
                if len(line) >= 3 and len(line) <= 40:
                    return line
        return "Merchant"

    elif document_type == "bank_statement":
        m = re.search(r"([A-Za-z\s]{3,30}\bBank\b|[A-Za-z\s]{3,30}\bBanking\b)", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
        return "Financial Institution"

    return "Document Issuer"


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

    origin = extract_station(r"^\s*Boarding At\b|^\s*From\b")
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
    """Generalized bus ticket extraction for any bus operator."""
    fields = {}
    full_text = "\n".join(l.get("text", "") for l in lines)
    issuer = detect_issuer(full_text, "bus")

    journey_line = get_next_line(lines, r"Journey Date and Time|Journey Date")
    if journey_line:
        match = re.search(
            r"(\d{1,2}/\d{1,2}/\d{4}),?\s*(\d{1,2}:\d{2}\s*[AP]M)?",
            journey_line["text"],
            re.IGNORECASE
        )
        if match:
            fields["journey_date"] = create_field(match.group(1), journey_line)
            if match.group(2):
                fields["departure_time"] = create_field(match.group(2), journey_line)

    boarding_line = get_next_line(lines, r"^\s*Boarding Point\s*$|^\s*From\s*$")
    if boarding_line:
        fields["origin"] = create_field(boarding_line["text"], boarding_line)

    dropping_line = get_next_line(lines, r"^\s*Dropping Point\s*$|^\s*To\s*$")
    if dropping_line:
        fields["destination"] = create_field(dropping_line["text"], dropping_line)

    operator_line = get_next_line(lines, r"^\s*Travels\s*$|^\s*Bus Operator\s*$")
    if operator_line:
        fields["operator"] = create_field(operator_line["text"], operator_line)

    price_line = get_line(lines, r"Ticket Price|Total Fare")
    if price_line:
        price_value_line = get_next_line(lines, r"Ticket Price|Total Fare")
        if price_value_line:
            price_match = re.search(
                r"(?:Rs\.?|₹|\$|€)\s*[\d,]+(?:\.\d{1,2})?",
                price_value_line["text"],
                re.IGNORECASE
            )
            if price_match:
                fields["ticket_price"] = create_field(price_match.group(0), price_value_line)

    seat_line = get_next_line(lines, r"^\s*Seat no\s*$|^\s*Seat\s*$")
    if seat_line:
        seat_value = seat_line["text"].strip().upper()
        if re.fullmatch(r"[A-Z0-9-]{1,10}", seat_value):
            fields["seat"] = create_field(seat_value, seat_line)

    arrival_line = get_next_line(lines, r"DROPPING DATE\s*&\s*TIME|Arrival Time")
    if arrival_line:
        match = re.search(
            r"(\d{1,2}/\d{1,2}/\d{4}),?\s*(\d{1,2}:\d{2}\s*[AP]M)?",
            arrival_line["text"],
            re.IGNORECASE
        )
        if match:
            fields["arrival_date"] = create_field(match.group(1), arrival_line)
            if match.group(2):
                fields["arrival_time"] = create_field(match.group(2), arrival_line)

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
