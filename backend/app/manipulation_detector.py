from pathlib import Path

from app.ela_detector import generate_ela
from app.metadata_detector import analyze_metadata
from app.visual_region_detector import analyze_visual_regions
from app.pdf_structure_detector import analyze_pdf_structure
from app.revision_detector import (
    inspect_revision_markers,
    analyze_prev_chain
)
from app.content_stream_detector import analyze_content_streams


def generate_findings_summary(checks, errors=None):
    """
    Consolidate forensic screening results into findings.

    Findings are indicators for review, not proof
    of document manipulation.
    """
    findings = []
    errors = errors or []

    # 1. Metadata findings
    metadata = checks.get("metadata", {})
    missing_fields = metadata.get("missing_metadata_fields", [])

    if missing_fields:
        findings.append({
            "category": "metadata",
            "severity": "info",
            "message": (
                "Some PDF metadata fields are missing: "
                + ", ".join(missing_fields)
            )
        })

    if metadata.get("xmp_comparison_status") == "warning":
        findings.append({
            "category": "metadata",
            "severity": "review",
            "message": (
                "Differences were found between PDF Info "
                "metadata and XMP metadata."
            )
        })

    for check in metadata.get("timestamp_checks", []):
        if check.get("status") == "failed":
            findings.append({
                "category": "metadata",
                "severity": "review",
                "message": check.get(
                    "message",
                    "A timestamp consistency issue was detected."
                )
            })

    # 2. Visual-region findings
    visual = checks.get("visual_regions", {})

    for page in visual.get("pages", []):
        page_number = page.get("page_number")
        font_count = page.get("font_anomaly_count", 0)
        color_count = page.get("color_anomaly_count", 0)
        overlap_count = page.get("overlap_count", 0)
        text_image_count = page.get("text_image_overlap_count", 0)

        anomaly_count = (
            font_count + color_count + overlap_count + text_image_count
        )

        if anomaly_count > 0:
            findings.append({
                "category": "visual_regions",
                "severity": "info",
                "page_number": page_number,
                "message": (
                    f"{anomaly_count} candidate visual "
                    f"anomaly/anomalies detected on page {page_number}. "
                    "These may result from normal document formatting. "
                    "Manual examination is needed to determine "
                    "their significance."
                )
            })

    # 3. PDF structural findings
    structure = checks.get("pdf_structure", {})
    signature = structure.get("signature_analysis", {})

    if signature.get("signature_object_count", 0) == 0:
        findings.append({
            "category": "digital_signature",
            "severity": "info",
            "message": (
                "No digital signature objects were detected. "
                "This does not establish document invalidity."
            )
        })

    for page in structure.get("page_analysis", []):
        annotation_count = page.get("annotation_count", 0)

        if annotation_count > 0:
            page_number = page.get("page_number")
            findings.append({
                "category": "pdf_annotations",
                "severity": "review",
                "page_number": page_number,
                "annotation_count": annotation_count,
                "message": (
                    f"{annotation_count} PDF annotation(s) detected "
                    f"on page {page_number}. Review comments, highlights, "
                    "and other annotations to determine their purpose."
                )
            })

    # 4. Revision-history findings
    revision = checks.get("revision_chain", {})
    revision_count = revision.get("incremental_revision_count")

    if (
        not revision.get("is_linearized", False)
        and isinstance(revision_count, int)
        and revision_count > 0
    ):
        findings.append({
            "category": "revision_history",
            "severity": "review",
            "message": (
                f"{revision_count} additional incremental revision(s) "
                "detected. Review revision history to understand "
                "the changes."
            )
        })

    # 5. Content-stream findings
    content_stream = checks.get("content_stream_analysis", {})

    for item in content_stream.get("findings", []):
        findings.append({
            "category": "content_stream",
            "severity": item.get("severity", "warning"),
            "page_number": item.get("page"),
            "message": (
                "Possible PDF text replacement pattern detected: "
                "an empty text block and a separate text-showing "
                "object occur at nearly identical coordinates. "
                "This requires manual review and is not proof "
                "of document manipulation."
            ),
            "details": {
                "finding": item.get("finding"),
                "original_stream": item.get("original_stream"),
                "replacement_stream": item.get("replacement_stream"),
                "position": item.get("position")
            }
        })

    # 6. Analysis errors
    for error in errors:
        if isinstance(error, dict):
            module = error.get("module", "unknown")
            message = error.get("error", str(error))
            error_message = f"{module}: {message}"
        else:
            error_message = str(error)

        findings.append({
            "category": "analysis_error",
            "severity": "warning",
            "message": error_message
        })

    # 7. Overall assessment
    requires_review = any(
        finding.get("severity") in ("review", "warning")
        for finding in findings
    )

    overall_assessment = (
        "review_recommended"
        if requires_review
        else "no_significant_indicators_detected"
    )

    return {
        "findings": findings,
        "finding_count": len(findings),
        "overall_assessment": overall_assessment,
        "interpretation": (
            "This assessment summarizes automated forensic screening "
            "indicators. It does not establish whether a document is "
            "genuine or forged. Manual examination and independent "
            "verification may still be required."
        )
    }


def analyze_manipulation(file_path: Path, output_dir: Path):
    """
    Coordinate forensic checks for an uploaded document.

    This is a forensic screening system, not a definitive
    document forgery classifier.
    """
    file_path = Path(file_path)
    output_dir = Path(output_dir)

    if not file_path.exists():
        raise FileNotFoundError(
            f"Input document not found: {file_path}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    results = {
        "file_name": file_path.name,
        "analysis_type": "manipulation_detection",
        "checks": {},
        "errors": []
    }

    # 1. Metadata analysis
    try:
        results["checks"]["metadata"] = analyze_metadata(file_path)
    except Exception as error:
        results["errors"].append({
            "module": "metadata",
            "error": str(error)
        })

    # 2. Error Level Analysis
    try:
        ela_output_dir = output_dir / "ela_analysis"
        ela_output_dir.mkdir(parents=True, exist_ok=True)

        results["checks"]["ela"] = generate_ela(
            file_path,
            ela_output_dir
        )
    except Exception as error:
        results["errors"].append({
            "module": "ela",
            "error": str(error)
        })

    # 3. Visual-region analysis
    try:
        results["checks"]["visual_regions"] = (
            analyze_visual_regions(file_path)
        )
    except Exception as error:
        results["errors"].append({
            "module": "visual_regions",
            "error": str(error)
        })

    # 4. PDF structural analysis
    try:
        results["checks"]["pdf_structure"] = (
            analyze_pdf_structure(file_path)
        )
    except Exception as error:
        results["errors"].append({
            "module": "pdf_structure",
            "error": str(error)
        })

    # 5. Revision-marker analysis
    try:
        results["checks"]["revision_markers"] = (
            inspect_revision_markers(file_path)
        )
    except Exception as error:
        results["errors"].append({
            "module": "revision_markers",
            "error": str(error)
        })

    # 6. Previous revision-chain analysis
    try:
        results["checks"]["revision_chain"] = (
            analyze_prev_chain(file_path)
        )
    except Exception as error:
        results["errors"].append({
            "module": "revision_chain",
            "error": str(error)
        })

    # 7. PDF content-stream analysis
    try:
        content_stream_result = analyze_content_streams(file_path)
        results["checks"]["content_stream_analysis"] = content_stream_result

        # Keep this top-level key for compatibility with the existing API.
        results["content_stream_analysis"] = content_stream_result
    except Exception as error:
        results["errors"].append({
            "module": "content_stream_analysis",
            "error": str(error)
        })

    # Build the summary only after all checks have run.
    results["summary"] = generate_findings_summary(
        results["checks"],
        results["errors"]
    )

    results["status"] = (
        "completed_with_errors"
        if results["errors"]
        else "completed"
    )

    results["interpretation"] = (
        "Forensic indicators are reported separately. "
        "They must be interpreted together and do not "
        "independently establish document forgery."
    )

    return results
