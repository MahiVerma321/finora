
from app.authenticity.field_merger import merge_fields


specific_fields = {
    "origin": {
        "value": "BHUBANESWAR",
        "confidence": 0.99
    },
    "destination": {
        "value": "DEHRADUN",
        "confidence": 0.98
    }
}

generic_fields = {
    "origin": {
        "value": "BHUBANESWAR AIRPORT",
        "confidence": 0.95
    },
    "destination": {
        "value": "DEHRADUN",
        "confidence": 0.97
    },
    "seat": {
        "value": "23A",
        "confidence": 0.99
    }
}


result = merge_fields(specific_fields, generic_fields)

print("========== MERGED FIELDS ==========")

for name, field in result["fields"].items():
    print(name, ":", field["value"])

print("\n========== COMPARISONS ==========")

for name, status in result["comparisons"].items():
    print(name, ":", status)

print("\n========== CONFLICTS ==========")

for name, conflict in result["conflicts"].items():
    print(name, ":", conflict)
