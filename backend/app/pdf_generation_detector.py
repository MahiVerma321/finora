
import pymupdf
import pikepdf
from pathlib import Path

from app.provenance_detector import analyze_provenance


def analyze_pdf_generation(pdf_path):
    """
    Analyze PDF forensic characteristics that may help identify
    generated, reconstructed, or digitally altered documents.

    These checks identify indicators, not definitive AI authorship.
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        return {
            "status": "failed",
            "error": "PDF file not found."
        }

    result = {
        "status": "completed",
        "analysis_type": "pdf_generation_forensics",
        "file_name": pdf_path.name,
        "checks": {
            "metadata": {},
            "document_structure": {},
            "fonts": {},
            "images": {},
            "page_analysis": {},
            "provenance": {}
        },
        "findings": [],
        "assessment": ""
    }

    try:
        # -------------------------------------------------
        # 1. METADATA ANALYSIS
        # -------------------------------------------------

        with pymupdf.open(pdf_path) as doc:
            metadata = doc.metadata or {}

            result["checks"]["metadata"] = {
                "title": metadata.get("title"),
                "author": metadata.get("author"),
                "creator": metadata.get("creator"),
                "producer": metadata.get("producer"),
                "creation_date": metadata.get("creationDate"),
                "modification_date": metadata.get("modDate"),
                "page_count": len(doc)
            }

            if not metadata.get("creator"):
                result["findings"].append({
                    "category": "metadata",
                    "indicator": "missing_creator",
                    "severity": "low",
                    "description": (
                        "The PDF does not contain creator information."
                    )
                })

            if not metadata.get("producer"):
                result["findings"].append({
                    "category": "metadata",
                    "indicator": "missing_producer",
                    "severity": "low",
                    "description": (
                        "The PDF does not contain producer information."
                    )
                })

            # -------------------------------------------------
            # 2. FONT ANALYSIS
            # -------------------------------------------------

            font_details = []
            unique_fonts = set()

            for page_number, page in enumerate(doc, start=1):
                for font in page.get_fonts(full=True):
                    font_xref = font[0]
                    font_name = font[3] or "Unknown"

                    unique_fonts.add(font_name)

                    try:
                        extracted_font = doc.extract_font(font_xref)
                        font_data = extracted_font[3]
                        is_embedded = bool(font_data)
                    except Exception:
                        is_embedded = None

                    font_details.append({
                        "page": page_number,
                        "font_name": font_name,
                        "font_type": font[2],
                        "embedded": is_embedded
                    })

            result["checks"]["fonts"] = {
                "total_font_references": len(font_details),
                "unique_font_count": len(unique_fonts),
                "unique_fonts": sorted(unique_fonts),
                "font_details": font_details
            }

            if len(unique_fonts) > 8:
                result["findings"].append({
                    "category": "fonts",
                    "indicator": "high_font_variety",
                    "severity": "low",
                    "description": (
                        "The document uses many different fonts. "
                        "This may be normal for complex documents."
                    )
                })

            # -------------------------------------------------
            # 3. IMAGE ANALYSIS
            # -------------------------------------------------

            image_details = []
            total_images = 0

            for page_number, page in enumerate(doc, start=1):
                images = page.get_images(full=True)
                total_images += len(images)

                for image in images:
                    image_details.append({
                        "page": page_number,
                        "xref": image[0],
                        "width": image[2],
                        "height": image[3]
                    })

            result["checks"]["images"] = {
                "total_image_references": total_images,
                "image_details": image_details
            }

            # -------------------------------------------------
            # 4. PAGE COMPOSITION ANALYSIS
            # -------------------------------------------------

            page_details = []

            for page_number, page in enumerate(doc, start=1):
                page_width = page.rect.width
                page_height = page.rect.height
                page_area = page_width * page_height

                # Extract text blocks
                text_blocks = page.get_text("blocks")

                text_area = 0

                for block in text_blocks:
                    if len(block) > 6 and block[6] == 0:
                        x0, y0, x1, y1 = block[:4]
                        text_area += (
                            max(0, x1 - x0) *
                            max(0, y1 - y0)
                        )

                # Extract image placements
                image_info = page.get_image_info(xrefs=True)

                image_area = 0

                for image in image_info:
                    bbox = image.get("bbox")

                    if bbox:
                        rect = pymupdf.Rect(bbox)
                        image_area += rect.width * rect.height

                # Extract vector drawing areas
                drawings = page.get_drawings()
                drawing_details = []

                for drawing in drawings:
                    rect = drawing.get("rect")

                    if rect:
                        drawing_details.append({
                            "type": drawing.get("type"),
                            "bbox": [
                                round(value, 2)
                                for value in rect
                            ],
                            "width": round(rect.width, 2),
                            "height": round(rect.height, 2),
                            "fill": drawing.get("fill"),
                            "stroke": drawing.get("color"),
                            "item_count": len(
                                drawing.get("items", [])
                            )
                        })

                drawing_area = 0

                for drawing in drawings:
                    rect = drawing.get("rect")

                    if rect:
                        drawing_area += rect.width * rect.height

                # Calculate approximate coverage percentages
                text_coverage = min(
                    100,
                    (text_area / page_area) * 100
                ) if page_area else 0

                image_coverage = min(
                    100,
                    (image_area / page_area) * 100
                ) if page_area else 0

                drawing_coverage = min(
                    100,
                    (drawing_area / page_area) * 100
                ) if page_area else 0

                extracted_text = page.get_text("text")

                page_details.append({
                    "page": page_number,
                    "width": round(page_width, 2),
                    "height": round(page_height, 2),

                    "rotation": page.rotation,

                    "media_box": [
                        round(value, 2)
                        for value in page.mediabox
                    ],

                    "crop_box": [
                        round(value, 2)
                        for value in page.cropbox
                    ],

                    "transformation_matrix": [
                        round(value, 4)
                        for value in page.transformation_matrix
                    ],

                    "text_character_count": len(extracted_text),
                    "text_block_count": len(text_blocks),
                    "image_count": len(image_info),
                    "drawing_count": len(drawings),

                    "drawing_details": drawing_details[:20],

                    "text_coverage_percent": round(
                        text_coverage, 2
                    ),

                    "image_coverage_percent": round(
                        image_coverage, 2
                    ),

                    "drawing_coverage_percent": round(
                        drawing_coverage, 2
                    ),

                    "has_extractable_text": bool(
                        extracted_text.strip()
                    )
                })

            result["checks"]["page_analysis"] = {
                "pages": page_details
            }

        # -------------------------------------------------
        # 5. PDF OBJECT STRUCTURE
        # -------------------------------------------------

        with pikepdf.open(pdf_path) as pdf:
            result["checks"]["document_structure"] = {
                "page_count": len(pdf.pages),
                "pdf_version": pdf.pdf_version,
                "object_count": len(pdf.objects),
                "encrypted": pdf.is_encrypted
            }


        # -------------------------------------------------
        # 6. AI PROVENANCE ANALYSIS
        # -------------------------------------------------

        result["checks"]["provenance"] = analyze_provenance(
            pdf_path
        )

        provenance = result["checks"]["provenance"]

        if (
            provenance.get("status") == "completed"
            and provenance.get("manifest_detected") is True
        ):
            provenance_details = provenance.get(
                "provenance", {}
            )

            platform_info = provenance.get(
                "platform_identification", {}
            )

            identified_platforms = platform_info.get(
                "identified_platforms", []
            )

            platform_names = [
                item.get("platform")
                for item in identified_platforms
            ]

            if provenance_details.get("ai_generation_declared"):
                result["findings"].append({
                    "category": "provenance",
                    "indicator": "ai_generation_declared",
                    "severity": "high",
                    "description": (
                        "The embedded C2PA provenance information "
                        "declares AI-generated content."
                    ),
                    "identified_platforms": platform_names,
                    "generator": provenance_details.get(
                        "generator_names"
                    ),
                    "issuer": provenance_details.get("issuer")
                })

            elif platform_names:
                result["findings"].append({
                    "category": "provenance",
                    "indicator": "ai_platform_declared",
                    "severity": "low",
                    "description": (
                        "An AI platform name was found in the "
                        "C2PA provenance information, but an "
                        "AI-generation declaration was not established."
                    ),
                    "identified_platforms": platform_names
                })


        # -------------------------------------------------
        # 7. FINAL ASSESSMENT
        # -------------------------------------------------

        result["assessment"] = (
            "PDF forensic characteristics and available "
            "provenance information have been analyzed. "
            "Results are technical indicators and do not "
            "independently establish the complete history "
            "or authorship of a document."
        )

        return result

    except Exception as error:
        return {
            "status": "failed",
            "analysis_type": "pdf_generation_forensics",
            "error": str(error)
        }
