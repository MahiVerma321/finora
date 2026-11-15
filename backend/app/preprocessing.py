
import io
from pathlib import Path

import cv2
import pymupdf
import numpy as np
from PIL import Image, ExifTags


def analyze_pdf(file_path: Path):
    """Extract basic forensic information from a PDF."""

    document = pymupdf.open(file_path)

    metadata = document.metadata or {}
    pages = []

    for page_number, page in enumerate(document):
        page_text = page.get_text("text")

        pages.append({
            "page_number": page_number + 1,
            "width": round(page.rect.width, 2),
            "height": round(page.rect.height, 2),
            "text": page_text[:5000],
            "text_length": len(page_text),
            "embedded_image_count": len(page.get_images(full=True)),
        })

    result = {
        "file_type": "PDF",
        "metadata": {
            "title": metadata.get("title"),
            "author": metadata.get("author"),
            "creator": metadata.get("creator"),
            "producer": metadata.get("producer"),
            "creation_date": metadata.get("creationDate"),
            "modification_date": metadata.get("modDate"),
        },
        "page_count": len(document),
        "pages": pages,
    }

    document.close()
    return result


def analyze_image(file_path: Path):
    """Extract image metadata and basic image properties."""

    with Image.open(file_path) as image:
        image_format = image.format
        width, height = image.size
        image_mode = image.mode

        exif_data = image.getexif()
        exif = {}

        for tag_id, value in exif_data.items():
            tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))

            # Avoid returning large or binary EXIF values.
            if isinstance(value, (str, int, float)):
                exif[tag_name] = value

        image_bytes = file_path.read_bytes()
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        decoded = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if decoded is None:
            raise ValueError("OpenCV could not decode this image.")

        gray = cv2.cvtColor(decoded, cv2.COLOR_BGR2GRAY)

        return {
            "file_type": "IMAGE",
            "format": image_format,
            "width": width,
            "height": height,
            "color_mode": image_mode,
            "channels": int(decoded.shape[2]),
            "grayscale_dimensions": {
                "width": int(gray.shape[1]),
                "height": int(gray.shape[0]),
            },
            "exif_metadata": exif,
        }


def analyze_document(file_path: Path):
    """Choose the appropriate preprocessing function."""

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return analyze_pdf(file_path)

    if extension in [".jpg", ".jpeg", ".png"]:
        return analyze_image(file_path)

    raise ValueError("Unsupported document format.")
