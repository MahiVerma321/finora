from app.authenticity.field_aliases import FIELD_ALIASES


def find_standard_field(label):

    label = label.lower().strip()
    label = label.rstrip(":.- ")

    for field, aliases in FIELD_ALIASES.items():

        if label in aliases:
            return field

    return None


test_labels = [
    "Boarding Point",
    "From",
    "Date of Journey",
    "Travel Date",
    "Seat No",
    "Berth",
    "Total Fare",
    "Passenger Name",
]

for label in test_labels:
    print(label, "->", find_standard_field(label))