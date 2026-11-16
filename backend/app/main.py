
from pathlib import Path
from uuid import uuid4
import os
import re

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.preprocessing import analyze_document
from app.ela_detector import generate_ela
from app.ocr_engine import extract_document_text
from app.authenticity.ticket_extractor import extract_ticket
from app.authenticity.consistency_detector import analyze_consistency
from app.manipulation_detector import analyze_manipulation, generate_findings_summary
from app.visual_evidence import generate_visual_evidence

# New central AI forensic detector
from app.ai_detector import analyze_ai_file


app = FastAPI(
    title="Digital Document Forensics API",
    description="Digital Document Forensics API for PDF and image analysis.",
    version="0.1.0",
)


# CORS origins are read from the CORS_ORIGINS environment variable so that
# the deployed frontend URL can be set without code changes.  The default
# keeps local development working without any env-var configuration.
_cors_origins_env = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
)
origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(os.getenv("FINORA_DATA_DIR", str(Path(__file__).resolve().parents[2]))).resolve()

UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", str(15 * 1024 * 1024)))
CHUNK_SIZE = 1024 * 1024

RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


app.mount(
    "/results",
    StaticFiles(directory=RESULTS_DIR),
    name="results"
)


# Validate file signatures rather than trusting browser-provided MIME type.
SIGNATURES = {
    "jpg": lambda b: b.startswith(b"\xff\xd8\xff"),
    "jpeg": lambda b: b.startswith(b"\xff\xd8\xff"),
    "png": lambda b: b.startswith(b"\x89PNG\r\n\x1a\n"),
    "pdf": lambda b: b.startswith(b"%PDF-"),
}


def validate_file_id(file_id: str):
    """Validate UUID-format file identifiers."""

    if not re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{12}",
        file_id
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid file ID."
        )


def find_uploaded_file(file_id: str):
    """Find an uploaded document using its UUID."""

    validate_file_id(file_id)

    for extension in ["pdf", "jpg", "jpeg", "png"]:
        candidate = UPLOAD_DIR / f"{file_id}.{extension}"

        if candidate.is_file():
            return candidate

    raise HTTPException(
        status_code=404,
        detail="Uploaded document not found."
    )


@app.get("/")
def root():
    return {
        "message": "Digital Document Forensics API is running"
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):

    original_name = Path(file.filename or "upload").name
    extension = Path(original_name).suffix.lower().lstrip(".")

    if extension not in SIGNATURES:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file. Upload JPG, JPEG, PNG or PDF."
        )

    # Read at most the configured limit plus one byte.
    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty."
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 15 MB limit."
        )

    if not SIGNATURES[extension](content[:16]):
        raise HTTPException(
            status_code=415,
            detail="File contents do not match the selected file extension."
        )

    file_id = str(uuid4())
    safe_name = f"{file_id}.{extension}"

    destination = UPLOAD_DIR / safe_name
    destination.write_bytes(content)

    return {
        "file_id": file_id,
        "original_filename": original_name,
        "stored_filename": safe_name,
        "file_type": extension.upper(),
        "size_bytes": len(content),
        "status": "uploaded",
        "message": "Upload successful."
    }


@app.get("/api/analyze/{file_id}")
def analyze_uploaded_document(file_id: str):

    file_path = find_uploaded_file(file_id)

    try:
        result = analyze_document(file_path)

        return {
            "file_id": file_id,
            "filename": file_path.name,
            "analysis_status": "completed",
            "preprocessing": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"Document preprocessing failed: {str(error)}"
        )


@app.get("/api/ela/{file_id}")
def run_ela_analysis(file_id: str):

    validate_file_id(file_id)

    file_path = None

    # ELA currently supports image uploads only.
    for extension in ["jpg", "jpeg", "png"]:
        candidate = UPLOAD_DIR / f"{file_id}.{extension}"

        if candidate.is_file():
            file_path = candidate
            break

    if file_path is None:
        raise HTTPException(
            status_code=404,
            detail="Image not found. ELA currently supports JPG, JPEG and PNG."
        )

    try:
        output_path = RESULTS_DIR / f"{file_id}_ela.png"

        result = generate_ela(
            file_path=file_path,
            output_path=output_path
        )

        return {
            "file_id": file_id,
            "analysis_status": "completed",
            "ela_analysis": result,
            "visualization_url": f"/results/{output_path.name}"
        }

    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"ELA analysis failed: {str(error)}"
        )


@app.get("/api/ocr/{file_id}")
def run_ocr(file_id: str):

    file_path = find_uploaded_file(file_id)

    try:
        result = extract_document_text(file_path)

        return {
            "file_id": file_id,
            "analysis_status": "completed",
            "ocr_result": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"OCR analysis failed: {str(error)}"
        )


@app.get("/api/consistency/{file_id}")
def run_consistency_analysis(file_id: str):

    file_path = find_uploaded_file(file_id)

    try:
        # Step 1: OCR extraction
        ocr_result = extract_document_text(file_path)

        # Step 2: Structured ticket extraction
        ticket = extract_ticket(ocr_result)

        # Step 3: Combined consistency and field validation
        validation_report = analyze_consistency(ticket)

        return {
            "file_id": file_id,
            "analysis_status": "completed",
            "document_type": ticket.get("document_type"),
            "document_category": ticket.get("document_category"),
            "document_label": ticket.get("document_label"),
            "issuer": ticket.get("issuer"),
            "extracted_document": ticket,
            "extracted_ticket": ticket,
            "consistency_report": {
                "status": validation_report["status"],
                "summary": validation_report["summary"],
                "checks": validation_report["checks"]
            },
            "field_validation_report": (
                validation_report["field_validation_report"]
            ),
            "overall_status": validation_report["overall_status"]
        }

    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"Consistency analysis failed: {str(error)}"
        )


@app.get("/api/manipulation/{file_id}")
def run_manipulation_analysis(file_id: str):

    validate_file_id(file_id)

    # Locate uploaded PDF
    file_path = UPLOAD_DIR / f"{file_id}.pdf"

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Uploaded PDF not found."
        )

    # Keep each document's analysis outputs separate.
    output_dir = RESULTS_DIR / file_id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = analyze_manipulation(
            file_path=file_path,
            output_dir=output_dir
        )

        # Add URLs for ELA visualizations.
        ela = result.get("checks", {}).get("ela", {})

        for page in ela.get("pages", []):
            visualization = page.get("visualization")

            if visualization:
                page["visualization_url"] = (
                    f"/results/{file_id}/"
                    f"{Path(visualization).name}"
                )

        # Generate PDF with suspected modification areas highlighted.
        content_analysis = result.get(
            "checks", {}
        ).get("content_stream_analysis", {})

        findings = content_analysis.get("findings", [])

        # Collect visual layout anomalies (e.g., text overlap, color/font deviations)
        # to ensure visual evidence is available for all document types, not only
        # documents with incremental content-stream replacements.
        visual_regions = result.get("checks", {}).get("visual_regions", {})
        visual_anomalies = []
        for page in visual_regions.get("pages", []):
            page_num = page.get("page_number", 1)
            for anomaly in page.get("anomalies", []):
                for key in ("bbox", "bbox_1", "bbox_2", "text_bbox"):
                    if anomaly.get(key):
                        visual_anomalies.append({
                            "page": page_num,
                            "type": anomaly.get("type", "visual_anomaly"),
                            "bbox": anomaly[key],
                            "text": anomaly.get("text", "")
                        })

        if findings or visual_anomalies:
            evidence_path = output_dir / "visual_evidence.pdf"

            try:
                evidence_result = generate_visual_evidence(
                    pdf_path=file_path,
                    findings=findings,
                    output_path=evidence_path,
                    visual_anomalies=visual_anomalies
                )
            except Exception as error:
                result["errors"].append({"module": "visual_evidence", "error": str(error)})
                result["status"] = "completed_with_errors"
                result["summary"] = generate_findings_summary(result["checks"], result["errors"])
                evidence_result = {"status": "unavailable", "highlighted_regions": 0}

            result["visual_evidence"] = {
                "status": evidence_result["status"],
                "highlighted_regions": evidence_result[
                    "highlighted_regions"
                ],
                "content_stream_highlights": evidence_result.get(
                    "content_stream_regions", 0
                ),
                "visual_anomaly_highlights": evidence_result.get(
                    "visual_anomaly_regions", 0
                ),
                "visualization_url": (
                    f"/results/{file_id}/visual_evidence.pdf"
                    if evidence_result.get("highlighted_regions", 0) > 0
                    else None
                )
            }

        else:
            result["visual_evidence"] = {
                "status": "no_regions_detected",
                "highlighted_regions": 0,
                "content_stream_highlights": 0,
                "visual_anomaly_highlights": 0,
                "visualization_url": None
            }

        return {
            "file_id": file_id,
            "analysis_status": result.get("status"),
            "manipulation_analysis": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"Manipulation analysis failed: {str(error)}"
        )


@app.get("/api/ai-content/{file_id}")
def run_ai_content_analysis(file_id: str):

    file_path = find_uploaded_file(file_id)

    try:
        # Run the new central AI forensic detector.
        result = analyze_ai_file(file_path)

        return {
            "file_id": file_id,
            "analysis_status": result.get("status"),
            "analysis_type": result.get("analysis_type"),
            "ai_content_analysis": result
        }

    except Exception as error:
        raise HTTPException(
            status_code=422,
            detail=f"AI content analysis failed: {str(error)}"
        )
