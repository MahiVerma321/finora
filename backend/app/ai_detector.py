
from pathlib import Path

from app.pdf_generation_detector import analyze_pdf_generation


def analyze_ai_file(file_path):
    """
    Central AI-content analysis controller.
    Routes uploaded files to the appropriate detector.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        return {
            "status": "failed",
            "error": "File not found."
        }

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        result = analyze_pdf_generation(file_path)

        return {
            "status": result.get("status", "failed"),
            "file_name": file_path.name,
            "file_type": "pdf",
            "analysis_type": "ai_content_forensics",
            "pdf_analysis": result,
            "assessment": result.get(
                "assessment",
                "PDF analysis could not be completed."
            )
        }

    if extension in [".png", ".jpg", ".jpeg", ".webp"]:
        return {
            "status": "pending",
            "file_name": file_path.name,
            "file_type": "image",
            "analysis_type": "ai_content_forensics",
            "assessment": (
                "Image analysis will be available "
                "after the image detector is integrated."
            )
        }

    return {
        "status": "unsupported",
        "file_name": file_path.name,
        "error": "This file type is not supported."
    }
