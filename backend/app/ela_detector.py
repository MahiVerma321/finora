
from pathlib import Path
from io import BytesIO
import tempfile

import pymupdf
import numpy as np
from PIL import Image, ImageChops, ImageEnhance


def generate_ela_from_image(
    image: Image.Image,
    output_path: Path,
    quality: int = 90
):
    """
    Generate an ELA visualization from a PIL image.
    This is a forensic visualization, not a forgery classifier.
    """

    original = image.convert("RGB")

    buffer = BytesIO()
    original.save(buffer, format="JPEG", quality=quality)
    buffer.seek(0)

    recompressed = Image.open(buffer).convert("RGB")

    difference = ImageChops.difference(
        original,
        recompressed
    )

    difference_array = np.asarray(
        difference, dtype=np.float32
    )

    mean_error = float(np.mean(difference_array))
    percentile_95 = float(
        np.percentile(difference_array, 95)
    )
    maximum_error = float(np.max(difference_array))

    scale = 255.0 / maximum_error if maximum_error > 0 else 1.0

    enhanced = ImageEnhance.Brightness(
        difference
    ).enhance(scale)

    output_path.parent.mkdir(
        parents=True, exist_ok=True
    )
    enhanced.save(output_path, format="PNG")

    return {
        "technique": "Error Level Analysis",
        "compression_quality": quality,
        "mean_error": round(mean_error, 4),
        "percentile_95_error": round(percentile_95, 4),
        "maximum_error": round(maximum_error, 4),
        "visualization": output_path.name,
        "interpretation": (
            "Compression differences are visible. "
            "These are common in PDF processing and do not "
            "independently indicate document manipulation."
        )
    }


def generate_ela(
    file_path: Path,
    output_path: Path,
    quality: int = 90
):
    """
    Generate ELA for JPEG, PNG, or PDF files.
    PDF pages are rendered individually.
    """

    extension = file_path.suffix.lower()

    if extension in [".jpg", ".jpeg", ".png"]:
        with Image.open(file_path) as image:
            return generate_ela_from_image(
                image, output_path, quality
            )

    if extension == ".pdf":
        document = pymupdf.open(file_path)
        page_results = []

        try:
            for page_index, page in enumerate(document):
                pixmap = page.get_pixmap(
                    matrix=pymupdf.Matrix(2, 2),
                    alpha=False
                )

                image = Image.frombytes(
                    "RGB",
                    [pixmap.width, pixmap.height],
                    pixmap.samples
                )

                page_output = output_path.parent / (
                    f"{output_path.stem}_page_{page_index + 1}.png"
                )

                result = generate_ela_from_image(
                    image,
                    page_output,
                    quality
                )

                result["page_number"] = page_index + 1
                page_results.append(result)

        finally:
            document.close()

        return {
            "technique": "PDF Page-wise Error Level Analysis",
            "page_count": len(page_results),
            "pages": page_results,
            "interpretation": (
                "PDF pages were rendered and analysed using ELA. "
                "This does not establish whether a page was manipulated."
            )
        }

    raise ValueError("Unsupported file format for ELA.")
