
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf
from paddleocr import PaddleOCR


@lru_cache(maxsize=1)
def get_ocr_engine():
    """
    Load the pretrained OCR model once.
    """
    return PaddleOCR(
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        engine="paddle",
    )


def read_result(result):
    """
    Convert PaddleOCR result into ordinary Python data.
    """
    raw = result.json if hasattr(result, "json") else result

    if callable(raw):
        raw = raw()

    if isinstance(raw, dict) and "res" in raw:
        raw = raw["res"]

    texts = raw.get("rec_texts", [])
    scores = raw.get("rec_scores", [])
    boxes = raw.get("rec_polys", [])

    lines = []

    for index, text in enumerate(texts):
        score = float(scores[index]) if index < len(scores) else None

        box = boxes[index] if index < len(boxes) else None

        if box is not None and hasattr(box, "tolist"):
            box = box.tolist()

        lines.append({
            "text": str(text),
            "confidence": round(score, 4) if score is not None else None,
            "box": box
        })

    return lines


def extract_from_image(image_path: Path):
    engine = get_ocr_engine()
    results = engine.predict(str(image_path))

    all_lines = []

    for page_number, result in enumerate(results, start=1):
        lines = read_result(result)

        for line in lines:
            line["page"] = page_number

        all_lines.extend(lines)

    return all_lines


def extract_from_pdf(pdf_path: Path):
    all_lines = []

    engine = get_ocr_engine()

    with TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)

        document = pymupdf.open(pdf_path)

        for page_index, page in enumerate(document):
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(2, 2),
                alpha=False
            )

            image_path = temp_dir / f"page_{page_index + 1}.png"
            pixmap.save(str(image_path))

            results = engine.predict(str(image_path))

            for result in results:
                lines = read_result(result)

                for line in lines:
                    line["page"] = page_index + 1

                all_lines.extend(lines)

        document.close()

    return all_lines


def extract_document_text(file_path: Path):
    extension = file_path.suffix.lower()

    if extension == ".pdf":
        lines = extract_from_pdf(file_path)

    elif extension in [".jpg", ".jpeg", ".png"]:
        lines = extract_from_image(file_path)

    else:
        raise ValueError("Unsupported document format.")

    full_text = "\n".join(
        line["text"] for line in lines
    )

    return {
        "technique": "PaddleOCR PP-OCRv6",
        "line_count": len(lines),
        "full_text": full_text,
        "lines": lines
    }
