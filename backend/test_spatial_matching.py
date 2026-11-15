from app.authenticity.spatial_matching import match_spatial_value


# Simulated OCR output.
# The label and value are on separate lines.

test_lines = [
    {
        "text": "Boarding Point",
        "confidence": 0.99,
        "page": 1,
        "box": [[100, 100], [200, 100], [200, 120], [100, 120]]
    },
    {
        "text": "Bhubaneswar",
        "confidence": 0.98,
        "page": 1,
        "box": [[100, 130], [200, 130], [200, 150], [100, 150]]
    },
    {
        "text": "Seat",
        "confidence": 0.99,
        "page": 1,
        "box": [[400, 100], [450, 100], [450, 120], [400, 120]]
    },
    {
        "text": "23A",
        "confidence": 0.99,
        "page": 1,
        "box": [[400, 130], [450, 130], [450, 150], [400, 150]]
    }
]


print("\n========== SPATIAL MATCHING TEST ==========\n")

for label in [test_lines[0], test_lines[2]]:

    result = match_spatial_value(label, test_lines)

    print("Label:", label["text"])
    print("Status:", result["status"])

    if result["status"] == "matched":
        print("Matched value:", result["candidate"]["text"])
        print("Spatial score:", result["score"])

    else:
        print("Reason:", result["reason"])

    print("--------------------------------")