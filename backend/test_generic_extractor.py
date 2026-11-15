
from app.authenticity.generic_extractor import extract_generic_fields


test_lines = [
    {
        "text": "Boarding Point",
        "confidence": 0.99,
        "page": 1,
        "box": None
    },
    {
        "text": "Bhubaneswar",
        "confidence": 0.98,
        "page": 1,
        "box": None
    },
    {
        "text": "Destination: Jamshedpur",
        "confidence": 0.97,
        "page": 1,
        "box": None
    },
    {
        "text": "Date of Journey",
        "confidence": 0.99,
        "page": 1,
        "box": None
    },
    {
        "text": "03-Nov-2026",
        "confidence": 0.99,
        "page": 1,
        "box": None
    },
    {
        "text": "Seat No: SU16",
        "confidence": 0.98,
        "page": 1,
        "box": None
    },
    {
        "text": "Total Fare: Rs. 783.75",
        "confidence": 0.99,
        "page": 1,
        "box": None
    },
]


result = extract_generic_fields(test_lines)

print("\n========== GENERIC EXTRACTION ==========\n")

for field_name, field_data in result["fields"].items():
    print(
        field_name,
        ":",
        field_data["value"],
        "| Confidence:",
        field_data["confidence"]
    )

print("\n========== AMBIGUOUS FIELDS ==========\n")

for field_name, details in result["ambiguous_fields"].items():
    print(field_name, ":", details["reason"])
