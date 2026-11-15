
from app.authenticity.ticket_extractor import extract_ticket


# Small sample inputs based on the three ticket layouts.
# All personal identifiers have been omitted.

flight_ocr = {
    "lines": [
        {"text": "IndiGo.", "confidence": 0.99, "page": 1, "box": None},
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
        {"text": "Journey Date and Time", "confidence": 0.99, "page": 1, "box": None},
        {"text": "03/11/2026, 09:45 PM", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Travels", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Shiv Shakti", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Ticket Price", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Rs. 783.75", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Boarding Point", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Bhubaneswar", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Dropping Point", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Jamshedpur", "confidence": 0.99, "page": 1, "box": None},
        {"text": "DROPPING DATE & TIME:", "confidence": 0.99, "page": 1, "box": None},
        {"text": "04/11/2026, 05:30 AM", "confidence": 0.99, "page": 1, "box": None},
        {"text": "Seat no", "confidence": 0.99, "page": 1, "box": None},
        {"text": "SU16", "confidence": 0.99, "page": 1, "box": None},
    ]
}


for name, sample in [
    ("FLIGHT", flight_ocr),
    ("TRAIN", train_ocr),
    ("BUS", bus_ocr),
]:
    print("\n==========", name, "==========")
    ticket = extract_ticket(sample)
    print("Type:", ticket["document_type"])
    print("Issuer:", ticket["issuer"])

    for field, details in ticket["fields"].items():
        print(field, ":", details["value"])
