from pathlib import Path
import json

from app.manipulation_detector import analyze_manipulation

INPUT_FILE = Path("test_revisions/original.pdf")

OUTPUT_DIR = Path("test_manipulation_output")


result = analyze_manipulation(
    INPUT_FILE,
    OUTPUT_DIR
)

print(
    json.dumps(
        result,
        indent=4,
        ensure_ascii=False,
        default=str
    )
)