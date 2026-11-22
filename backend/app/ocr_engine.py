import gc
import os
from functools import lru_cache
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock

import pymupdf

_OCR_LOCK = Lock()


@lru_cache(maxsize=1)
def _get_paddleocr_class():
    # Paddle/PaddleX are large imports and may probe remote model hosts. Native
    # PDF consistency checks must not pay this cost or load the inference runtime.
    os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")
    try:
        from paddleocr import PaddleOCR
    except ImportError:
        return None
    return PaddleOCR


@lru_cache(maxsize=1)
def get_ocr_engine():
    """
    Load lightweight PaddleOCR models once.
    Uses PP-OCRv6 small models to reduce resource usage.
    """
    PaddleOCR = _get_paddleocr_class()
    if PaddleOCR is None:
        return None

    return PaddleOCR(
        text_detection_model_name="PP-OCRv6_small_det",
        text_recognition_model_name="PP-OCRv6_small_rec",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        device="cpu",
        cpu_threads=2,
        enable_mkldnn=False,
        text_recognition_batch_size=1,
        engine="paddle",
    )

def run_ocr(image_path: Path):
    """
    Allow only one OCR inference at a time.
    Also protects first-time model initialization.
    """
    with _OCR_LOCK:
        engine = get_ocr_engine()

        if engine is None:
            return []

        return engine.predict(str(image_path))
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
    results = run_ocr(image_path)

    all_lines = []

    for page_number, result in enumerate(results, start=1):
        lines = read_result(result)

        for line in lines:
            line["page"] = page_number

        all_lines.extend(lines)

    return all_lines

def extract_from_pdf_pymupdf(pdf_path: Path):
    """
    Fallback text and line extraction using PyMuPDF when PaddleOCR
    is not installed in the environment (e.g., Python 3.13+).
    """
    all_lines = []
    doc = pymupdf.open(pdf_path)

    try:
        for page_index, page in enumerate(doc, start=1):
            text_dict = page.get_text("dict")
            for block in text_dict.get("blocks", []):
                if block.get("type") != 0:
                    continue
                for line in block.get("lines", []):
                    line_text = "".join(
                        span.get("text", "") for span in line.get("spans", [])
                    ).strip()
                    if not line_text:
                        continue
                    all_lines.append({
                        "text": line_text,
                        "confidence": 1.0,
                        "box": [round(val, 2) for val in line.get("bbox", [])],
                        "page": page_index
                    })
    finally:
        doc.close()

    return all_lines



def extract_from_pdf(pdf_path: Path):
    """
    Extract OCR text one PDF page at a time.
    Release temporary image and OCR objects to reduce peak memory.
    """
    if _get_paddleocr_class() is None:
        return extract_from_pdf_pymupdf(pdf_path)

    all_lines = []

    with TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        document = pymupdf.open(pdf_path)

        try:
            for page_index in range(len(document)):
                page = document.load_page(page_index)

                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(2, 2),
                    alpha=False
                )

                image_path = temp_dir / f"page_{page_index + 1}.png"
                pixmap.save(str(image_path))

                del pixmap
                del page

                results = run_ocr(image_path)

                for result in results:
                    lines = read_result(result)

                    for line in lines:
                        line["page"] = page_index + 1

                    all_lines.extend(lines)

                del results
                gc.collect()

        finally:
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

    technique = (
        "PaddleOCR PP-OCRv6"
        if _get_paddleocr_class() is not None
        else "PyMuPDF native text extraction (PaddleOCR optional)"
    )

    return {
        "technique": technique,
        "line_count": len(lines),
        "full_text": full_text,
        "lines": lines
    }


def _native_page_lines(page, page_number):
    # Exclude embedded image bytes: get_text("dict") otherwise copies them even
    # though only text blocks are needed.
    flags = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_IMAGES
    lines = []
    for block in page.get_text("dict", flags=flags, sort=True).get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            text = "".join(
                span.get("text", "") for span in line.get("spans", [])
            ).strip()
            if not text or not any(char.isalnum() for char in text):
                continue
            x0, y0, x1, y1 = (round(value, 2) for value in line["bbox"])
            lines.append({
                "text": text,
                "confidence": 1.0,
                "box": [[x0, y0], [x1, y0], [x1, y1], [x0, y1]],
                "page": page_number,
            })
    return lines


def extract_consistency_text(file_path: Path):
    """Use native PDF text where available and OCR only pages needing it.

    This path is specific to consistency; the explicit OCR endpoint retains its
    full-page OCR behavior. No Paddle imports or model downloads are needed for
    ordinary text PDFs.
    """
    if file_path.suffix.lower() != ".pdf":
        result = extract_document_text(file_path)
        if not result["full_text"].strip():
            raise ValueError("No readable text was extracted from the document.")
        return result

    all_lines = []
    techniques = set()
    with pymupdf.open(file_path) as document, TemporaryDirectory() as temp_dir:
        for page_number, page in enumerate(document, start=1):
            lines = _native_page_lines(page, page_number)
            # A scan can have a small selectable footer. Do not let that footer
            # hide the scanned body of the page from consistency analysis.
            page_area = page.rect.get_area()
            has_large_image = page_area > 0 and any(
                (pymupdf.Rect(info["bbox"]) & page.rect).get_area() >= page_area * 0.5
                for info in page.get_image_info()
            )
            if lines and not has_large_image:
                all_lines.extend(lines)
                techniques.add("PyMuPDF native text extraction")
                continue

            image_path = Path(temp_dir) / "page.png"
            # Bound allocations *before* rasterizing oversized PDF pages.
            scale = min(2.0, 1800 / max(page.rect.width, page.rect.height))
            pixmap = page.get_pixmap(
                matrix=pymupdf.Matrix(scale, scale),
                colorspace=pymupdf.csRGB,
                alpha=False,
            )
            pixmap.save(str(image_path))
            del pixmap
            try:
                if _get_paddleocr_class() is None:
                    raise RuntimeError("Scanned document text requires PaddleOCR, which is unavailable.")
                page_lines = extract_from_image(image_path)
                for line in page_lines:
                    line["page"] = page_number
                all_lines.extend(page_lines)
                techniques.add("PaddleOCR PP-OCRv6")
            finally:
                image_path.unlink(missing_ok=True)

    full_text = "\n".join(line["text"] for line in all_lines)
    if not full_text.strip():
        raise ValueError("No readable text was extracted from the document.")
    return {
        "technique": " + ".join(sorted(techniques)),
        "line_count": len(all_lines),
        "full_text": full_text,
        "lines": all_lines,
    }
