
from pathlib import Path
import re
import pymupdf


def inspect_pdf_trailer(document):
    """Inspect the PDF trailer for structural references."""

    try:
        trailer = document.pdf_trailer()
    except Exception:
        trailer = ""

    previous_revision = re.search(
        r"/Prev\s+(\d+)",
        trailer
    )

    xref_stream = re.search(
        r"/XRefStm\s+(\d+)",
        trailer
    )

    return {
        "trailer_available": bool(trailer),
        "has_previous_revision": bool(previous_revision),
        "previous_revision_offset": (
            int(previous_revision.group(1))
            if previous_revision else None
        ),
        "has_xref_stream": bool(xref_stream),
        "xref_stream_offset": (
            int(xref_stream.group(1))
            if xref_stream else None
        )
    }


def inspect_pdf_objects(document):
    """Count and classify PDF indirect objects."""

    object_count = max(0, document.xref_length() - 1)

    object_types = {
        "pages": 0,
        "fonts": 0,
        "images": 0,
        "annotations": 0,
        "forms": 0,
        "signatures": 0,
        "other": 0
    }

    for xref in range(1, document.xref_length()):

        try:
            obj = document.xref_object(xref)
        except Exception:
            object_types["other"] += 1
            continue

        if re.search(r"/Type\s*/Page(?!s)\b", obj):
            object_types["pages"] += 1

        elif re.search(r"/Type\s*/Font\b", obj):
            object_types["fonts"] += 1

        elif re.search(r"/Subtype\s*/Image\b", obj):
            object_types["images"] += 1

        elif re.search(r"/Type\s*/Annot\b", obj):
            if re.search(r"/Subtype\s*/Link\b", obj):
                object_types.setdefault("links", 0)
                object_types["links"] += 1
            else:
                object_types["annotations"] += 1

        elif re.search(r"/Type\s*/Sig\b|/FT\s*/Sig\b", obj):
            object_types["signatures"] += 1

        elif re.search(r"/AcroForm\b|/FT\s*/", obj):
            object_types["forms"] += 1

        else:
            object_types["other"] += 1

    return {
        "indirect_object_count": object_count,
        "object_type_counts": object_types
    }


def inspect_page_features(document):
    """Inspect annotations, form widgets, fonts and images."""

    pages = []

    for page_number, page in enumerate(document, start=1):

        try:
            annotations = list(page.annots() or [])
        except Exception:
            annotations = []

        try:
            links = page.get_links()
        except Exception:
            links = []

        try:
            widgets = list(page.widgets() or [])
        except Exception:
            widgets = []

        try:
            fonts = page.get_fonts(full=True)
        except Exception:
            fonts = []

        try:
            images = page.get_images(full=True)
        except Exception:
            images = []

        pages.append({
            "page_number": page_number,
            "annotation_count": len(annotations),
            "link_count": len(links),
            "links": [
                {
                    "type": link.get("kind"),
                    "uri": link.get("uri"),
                    "xref": link.get("xref"),
                    "from": list(link.get("from", []))
                }
                for link in links
            ],
            "widget_count": len(widgets),
            "embedded_font_count": len(fonts),
            "image_reference_count": len(images)
        })

    return pages


def inspect_signature_information(document):
    """Inspect available PDF signature indicators."""

    try:
        signature_flags = document.get_sigflags()
    except Exception:
        signature_flags = None

    signature_objects = []

    for xref in range(1, document.xref_length()):

        try:
            obj = document.xref_object(xref)
        except Exception:
            continue

        if (
            re.search(r"/Type\s*/Sig\b", obj)
            or re.search(r"/FT\s*/Sig\b", obj)
        ):
            signature_objects.append(xref)

    return {
        "signature_flags": signature_flags,
        "signature_object_count": len(signature_objects),
        "signature_object_xrefs": signature_objects,
        "interpretation": (
            "Signature indicators are structural clues only. "
            "Cryptographic signature validation is required "
            "to establish signature validity."
        )
    }


def analyze_pdf_structure(file_path: Path):
    """Perform structural analysis of a PDF."""

    document = pymupdf.open(file_path)

    try:
        if not document.is_pdf:
            raise ValueError("The supplied file is not a PDF.")

        trailer_analysis = inspect_pdf_trailer(document)

        object_analysis = inspect_pdf_objects(document)

        page_analysis = inspect_page_features(document)

        signature_analysis = inspect_signature_information(
            document
        )

        annotation_object_analysis = inspect_annotation_objects(
            document
        )

        return {
            "technique": "PDF Structural Analysis",
            "page_count": document.page_count,
            "is_encrypted": document.is_encrypted,
            "trailer_analysis": trailer_analysis,
            "object_analysis": object_analysis,
            "page_analysis": page_analysis,
            "signature_analysis": signature_analysis,
            "interpretation": (
                "Structural indicators can identify PDF features "
                "that deserve further inspection. They do not "
                "independently establish document authenticity "
                "or manipulation."
            ),
            "annotation_object_analysis": annotation_object_analysis
        }

    finally:
        document.close()


def inspect_annotation_objects(document):
    """Inspect annotation-related indirect PDF objects."""

    annotation_objects = []

    for xref in range(1, document.xref_length()):

        try:
            obj = document.xref_object(xref)
        except Exception:
            continue

        if re.search(r"/Type\s*/Annot\b", obj):

            annotation_objects.append({
                "xref": xref,
                "object": obj[:1000]
            })

    return {
        "annotation_object_count": len(annotation_objects),
        "annotation_objects": annotation_objects
    }
