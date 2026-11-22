

from app.authenticity.ticket_extractor import extract_ticket


# Synthetic regression samples.
# Personal identifiers are fictional or omitted.

flight_ocr = {
    "lines": [
        {"text": "IndiGo", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Boarding Pass (Web Check-In)", "confidence": 0.99, "page": 1, "box": None},
        {"text": "BHUBANESWAR (T1) To DEHRADUN (-)", "confidence": 0.99, "page": 1, "box": None},
        {"text": "6E 6321", "confidence": 0.99, "page": 1, "box": None},
        {"text": "13 Jan 2026", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Boarding Time", "confidence": 0.99, "page": 1, "box": None},
        {"text": "05:35 hrs", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Departure 06:20", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Seat", "confidence": 0.99, "page": 1, "box": None},
        {"text": "23A", "confidence": 0.99, "page": 1, "box": None},
        {"text": "TEST/ PASSENGER/MR", "confidence": 0.99, "page": 1, "box": None},
    ]
}

train_ocr = {
    "lines": [
        {"text": "Electronic Reservation Slip (ERS)-Normal User", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Boarding At", "confidence": 0.99, "page": 1, "box": None},
        {"text": "KANPUR CENTRAL JN. (CNB)", "confidence": 0.99, "page": 1, "box": None},
        {"text": "To", "confidence": 0.99, "page": 1, "box": None},
        {"text": "TATANAGAR JN. (TATA)", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Start Date*03-Nov-2026", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Departure* 14:25 03-Nov-2026", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Arrival*10:20 04-Nov-2026", "confidence": 0.99, "page": 1, "box": None},
        {"text": "18102/JAT TATA EXPRESS", "confidence": 0.99, "page": 1, "box": None},
    ]
}

bus_ocr = {
    "lines": [
        {"text": "Ticket Information", "confidence": 0.99, "page": 1, "box": None},
        {"text": "redBus", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Bhubaneswar-Jamshedpur on Tuesday, 03 November 2026", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Ticket Number: TVBV33716574", "confidence": 0.99, "page": 1, "box": None},
        {"text": "PNR No: 53278", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Hey Mahi Verma,", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Journey Date and Time", "confidence": 0.99, "page": 1, "box": None},
        {"text": "03/11/2026, 09:45 PM", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Travels", "confidence": 0.99, "page": 1, "box": None},
        {"text": "日", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Shiv Shakti", "confidence": 0.99, "page": 1, "box": None},
        {"text": "A/C Sleeper (2+1)", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Ticket Price", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Rs. 783.75", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Boarding Point", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Bhubaneswar", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Baramunda old bus stand", "confidence": 0.99, "page": 1, "box": None},
        {"text": "old baramunda parking", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Dropping Point", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Jamshedpur", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Mango Bus Stand", "confidence": 0.99, "page": 1, "box": None},
        {"text": "DROPPING DATE & TIME:", "confidence": 0.99, "page": 1, "box": None},
        {"text": "04/11/2026, 05:30 AM", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Passenger Details", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Seat no", "confidence": 0.99, "page": 1, "box": None},
        {"text": "2", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Mahi Verma", "confidence": 0.99, "page": 1, "box": None},
        {"text": "SU16", "confidence": 0.99, "page": 1, "box": None},
        {"text": "19Yrs, FEMALE", "confidence": 0.99, "page": 1, "box": None},
    ]
}


EXPECTED_FIELDS = {
    "FLIGHT": [
        "origin",
        "destination",
        "flight_number",
        "departure_date",
        "departure_time",
        "boarding_time",
        "seat",
        "passenger_name",
    ],
    "TRAIN": [
        "origin",
        "destination",
        "train_number",
        "train_name",
        "journey_date",
        "departure_time",
        "arrival_time",
        "arrival_date",
    ],
    "BUS": [
        "ticket_number",
        "pnr",
        "passenger_name",
        "origin",
        "destination",
        "operator",
        "journey_date",
        "departure_time",
        "arrival_date",
        "arrival_time",
        "seat",
        "ticket_price",
        "boarding_point",
        "dropping_point",
        "travel_class",
    ],
}


TEST_CASES = [
    ("FLIGHT", flight_ocr, "flight"),
    ("TRAIN", train_ocr, "train"),
    ("BUS", bus_ocr, "bus"),
]


for name, sample, expected_type in TEST_CASES:
    print("\n" + "=" * 55)
    print(f"{name} TICKET")
    print("=" * 55)

    ticket = extract_ticket(sample)

    print("Document type:", ticket.get("document_type"))
    print("Issuer:", ticket.get("issuer"))

    actual_type = ticket.get("document_type")

    if actual_type == expected_type:
        print("Classification: PASS")
    else:
        print(f"Classification: FAIL (expected {expected_type})")

    extracted_fields = ticket.get("fields", {})

    print("\nEXTRACTED FIELDS:")

    for field, details in extracted_fields.items():
        value = details.get("value") if isinstance(details, dict) else details
        print(f"{field:20} : {value}")

    print("\nEXPECTED FIELD CHECK:")

    missing_fields = []

    for field in EXPECTED_FIELDS[name]:
        details = extracted_fields.get(field)
        value = details.get("value") if isinstance(details, dict) else details

        if value is None or str(value).strip() == "":
            print(f"MISSING  : {field}")
            missing_fields.append(field)
        else:
            print(f"FOUND    : {field}")

    if not missing_fields:
        print("\nAll expected fields were extracted.")

    print("\nOBSERVATIONS:")
    observations = ticket.get("observations", {})

    for key, value in observations.items():
        print(f"{key}: {value}")

    print("\nSUMMARY:")
    print("Expected fields:", len(EXPECTED_FIELDS[name]))
    print("Missing fields:", len(missing_fields))
    print("Missing list:", missing_fields)
