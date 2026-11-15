from app.authenticity.ticket_schema import make_ticket
from app.authenticity.consistency_detector import analyze_consistency


# -------------------------
# TEST 1: FLIGHT TICKET
# -------------------------

flight = make_ticket(
    document_type="flight",
    issuer="IndiGo",
    fields={
        "flight_number": "6E 6321",
        "origin": "Bhubaneswar",
        "destination": "Dehradun",
        "departure_date": "13 Jan 2026",
        "boarding_time": "05:35",
        "departure_time": "06:20",
        "passenger_name": "TEST PASSENGER",
        "seat": "23A"
    },
    observations={
        "flight_number": ["6E 6321", "6E 6321"],
        "seat": ["23A", "23B"],
        "departure_date": ["13 Jan 2026", "13 Jan 2026"]
    }
)


# -------------------------
# TEST 2: TRAIN TICKET
# -------------------------

train = make_ticket(
    document_type="train",
    issuer="IRCTC",
    fields={
        "train_number": "18102",
        "origin": "Kanpur Central",
        "destination": "Tatanagar",
        "journey_date": "03-Nov-2026"
    },
    observations={
        "train_number": ["18102", "18102"],
        "journey_date": ["03-Nov-2026", "03-Nov-2026"]
    }
)


# -------------------------
# TEST 3: BUS TICKET
# -------------------------

bus = make_ticket(
    document_type="bus",
    issuer="redBus",
    fields={
        "origin": "Delhi",
        "destination": "Jaipur",
        "journey_date": "2026-11-10"
    },
    observations={
        "origin": ["Delhi", "Delhi"],
        "destination": ["Jaipur", "Jaipur"]
    }
)


# -------------------------
# RUN TESTS
# -------------------------

tickets = {
    "FLIGHT": flight,
    "TRAIN": train,
    "BUS": bus
}

for name, ticket in tickets.items():

    print("\n==============================")
    print(name, "TICKET")
    print("==============================")

    result = analyze_consistency(ticket)

    print("Overall status:", result["status"])
    print("Summary:", result["summary"])

    for check in result["checks"]:
        print(
            check["name"],
            "->",
            check["status"],
            "|",
            check["message"]
        )