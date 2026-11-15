
from pathlib import Path
from datetime import datetime, timezone

import pymupdf
from PIL import Image, ExifTags

import re
from datetime import datetime, timezone, timedelta

import hashlib
import xml.etree.ElementTree as ET

def get_file_information(file_path: Path):
    """Collect basic filesystem information."""

    stats = file_path.stat()

    return {
        "file_name": file_path.name,
        "file_size_bytes": stats.st_size,
        "file_modified_time": datetime.fromtimestamp(
            stats.st_mtime,
            tz=timezone.utc
        ).isoformat()
    }


def parse_pdf_date(value):
    """Parse a PDF date such as D:20261103031121+05'30'."""

    if not value:
        return None

    pattern = (
        r"^D:(\d{4})(\d{2})?(\d{2})?"
        r"(\d{2})?(\d{2})?(\d{2})?"
        r"([Z+\-])?(\d{2})?'?(\d{2})?'?$"
    )

    match = re.match(pattern, value.strip())

    if not match:
        return None

    year, month, day, hour, minute, second, sign, offset_h, offset_m = match.groups()

    try:
        date = datetime(
            int(year),
            int(month or 1),
            int(day or 1),
            int(hour or 0),
            int(minute or 0),
            int(second or 0)
        )

        if sign == "Z":
            date = date.replace(tzinfo=timezone.utc)

        elif sign in ("+", "-"):
            hours = int(offset_h or 0)
            minutes = int(offset_m or 0)

            offset = timedelta(
                hours=hours,
                minutes=minutes
            )

            if sign == "-":
                offset = -offset

            date = date.replace(
                tzinfo=timezone(offset)
            )

        return date

    except ValueError:
        return None


def calculate_sha256(file_path: Path):
    """Generate SHA-256 fingerprint of the uploaded file."""

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:
        for chunk in iter(lambda: file.read(8192), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def inspect_xmp_metadata(document):
    """Extract selected properties from PDF XMP metadata."""

    xml_data = document.get_xml_metadata()

    if not xml_data:
        return {
            "available": False,
            "metadata": {},
            "observations": ["No XMP metadata found."]
        }

    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError:
        return {
            "available": True,
            "metadata": {},
            "observations": ["XMP metadata could not be parsed."]
        }

    metadata = {}

    for element in root.iter():
        if element.text and element.text.strip():
            name = element.tag.split("}")[-1]
            metadata.setdefault(name, element.text.strip())

    return {
        "available": True,
        "metadata": metadata,
        "observations": []
    }


def compare_info_xmp(info, xmp):
    """Compare selected Info and XMP metadata fields."""

    comparisons = []

    mapping = {
        "title": "title",
        "author": "creator",
        "producer": "producer",
        "creator": "creatorTool",
        "creationDate": "createDate",
        "modDate": "modifyDate"
    }

    for info_field, xmp_field in mapping.items():
        info_value = info.get(info_field)
        xmp_value = xmp.get(xmp_field)

        if info_value and xmp_value:
            status = (
                "consistent"
                if info_value.strip().lower() == xmp_value.strip().lower()
                else "mismatch"
            )

            comparisons.append({
                "field": info_field,
                "info_value": info_value,
                "xmp_value": xmp_value,
                "status": status
            })

    return comparisons

def inspect_pdf_metadata(file_path: Path):
    """Extract PDF metadata and report observations."""

    document = pymupdf.open(file_path)

    try:
        metadata = document.metadata or {}

        xmp_result = inspect_xmp_metadata(document)

        xmp_metadata = xmp_result["metadata"]

        info_xmp_comparison = compare_info_xmp(
            metadata,
            xmp_metadata
        )

        if not xmp_result["available"]:
            xmp_comparison_status = "inconclusive"
        elif any(
            item["status"] == "mismatch"
            for item in info_xmp_comparison
        ):
            xmp_comparison_status = "warning"
        elif info_xmp_comparison:
            xmp_comparison_status = "consistent"
        else:
            xmp_comparison_status = "inconclusive"

        metadata_fields = [
            "title",
            "author",
            "subject",
            "keywords",
            "creator",
            "producer",
            "creationDate",
            "modDate",
            "format",
            "encryption"
        ]

        extracted_metadata = {
            field: metadata.get(field)
            for field in metadata_fields
        }

        missing_fields = [
            field
            for field in [
                "title",
                "author",
                "creator",
                "producer",
                "creationDate",
                "modDate"
            ]
            if not metadata.get(field)
        ]

        observations = []

        if missing_fields:
            observations.append({
                "type": "missing_metadata",
                "fields": missing_fields,
                "message": (
                    "Some PDF metadata fields are missing. "
                    "This is common and does not prove manipulation."
                )
            })

        creation_date = metadata.get("creationDate")
        modification_date = metadata.get("modDate")

        parsed_creation = parse_pdf_date(creation_date)
        parsed_modification = parse_pdf_date(modification_date)

        timestamp_checks = []

        if parsed_creation and parsed_modification:
            if parsed_modification < parsed_creation:
                timestamp_checks.append({
                    "status": "warning",
                    "message": (
                        "PDF modification timestamp is earlier "
                        "than its creation timestamp."
                    )
                })
            else:
                timestamp_checks.append({
                    "status": "passed",
                    "message": (
                        "PDF creation and modification timestamps "
                        "are chronologically consistent."
                    )
                })
        else:
            timestamp_checks.append({
                "status": "inconclusive",
                "message": "Could not reliably parse both PDF timestamps."
            })

        if creation_date and modification_date:
            observations.append({
                "type": "timestamp_available",
                "message": (
                    "Both creation and modification timestamps "
                    "are available for further examination."
                )
            })

        return {
            "technique": "PDF Metadata Analysis",
            "metadata": extracted_metadata,
            "page_count": len(document),
            "is_encrypted": document.is_encrypted,
            "missing_metadata_fields": missing_fields,
            "observations": observations,
            "file_information": get_file_information(file_path),
            "parsed_creation_date": (
                parsed_creation.isoformat() if parsed_creation else None
            ),
            "parsed_modification_date": (
                parsed_modification.isoformat() if parsed_modification else None
            ),
            "timestamp_checks": timestamp_checks,
            "xmp_metadata": xmp_result,
            "info_xmp_comparison": info_xmp_comparison,
            "sha256": calculate_sha256(file_path),
            "xmp_comparison_status": xmp_comparison_status
        }

    finally:
        document.close()


def inspect_image_metadata(file_path: Path):
    """Extract image properties and EXIF metadata."""

    with Image.open(file_path) as image:
        exif_data = image.getexif()

        extracted_exif = {}

        for tag_id, value in exif_data.items():
            tag_name = ExifTags.TAGS.get(
                tag_id, str(tag_id)
            )

            if isinstance(value, (str, int, float)):
                extracted_exif[tag_name] = value

        missing_fields = [
            field
            for field in [
                "DateTime",
                "Software",
                "Make",
                "Model"
            ]
            if field not in extracted_exif
        ]

        return {
            "technique": "Image Metadata Analysis",
            "format": image.format,
            "width": image.width,
            "height": image.height,
            "exif_metadata": extracted_exif,
            "missing_metadata_fields": missing_fields,
            "file_information": get_file_information(file_path)
        }


def analyze_metadata(file_path: Path):
    """Select metadata analysis based on file extension."""

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return inspect_pdf_metadata(file_path)

    if extension in [".jpg", ".jpeg", ".png"]:
        return inspect_image_metadata(file_path)

    raise ValueError("Unsupported file format for metadata analysis.")
