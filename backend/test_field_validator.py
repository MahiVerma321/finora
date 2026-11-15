
from app.authenticity.field_validator import validate_extracted_fields


def make_field(value):
    return {
        "value": value,
        "confidence": 0.99,
    }


# Sample flight fields
flight = {
    "fields": {
        "origin": make_field("BHUBANESWAR"),
        "destination": make_field("DEHRADUN"),
        "departure_date": make_field("13 Jan 2026"),
        "boarding_time": make_field("05:35"),
        "departure_time": make_field("06:20"),
        "flight_number": make_field("6E 6321"),
    }
}

# Sample train fields
train = {
    "fields": {
        "origin": make_field("KANPUR CENTRAL JN."),
        "destination": make_field("TATANAGAR JN."),
        "journey_date": make_field("03-Nov-2026"),
        "departure_time": make_field("14:25"),
        "arrival_time": make_field("10:20"),
        "train_number": make_field("18102"),
    }
}

# Sample bus fields
bus = {
    "fields": {
        "origin": make_field("Bhubaneswar"),
        "destination": make_field("Jamshedpur"),
        "journey_date": make_field("03/11/2026"),
        "departure_time": make_field("09:45 PM"),
        "arrival_date": make_field("04/11/2026"),
        "arrival_time": make_field("05:30 AM"),
        "ticket_price": make_field("Rs. 783.75"),
    }
}


def run_test(name, document):
    print(f"\n========== {name} VALIDATION ==========")

    result = validate_extracted_fields(document)

    for check in result["checks"]:
        print(
            f"{check['field']} : "
            f"{check['status']} | "
            f"{check['message']}"
        )

    print("\nSummary:", result["summary"])


run_test("FLIGHT", flight)
run_test("TRAIN", train)
run_test("BUS", bus)
