# FINORA — Digital Document Forensics & Origin Verification

Screen digital documents for possible alterations and examine available origin information, presenting understandable evidence for human review.

> **Important**: FINORA assists reviewers by highlighting anomalies, layout inconsistencies, revision markers, content stream manipulations, and cryptographic provenance (C2PA). It does not claim to prove authenticity or forgery definitively.

## Requirements

- Python 3.10+
- Node.js 18+
- npm

## 1. Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Environment Configuration

The backend supports configurable settings via environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGINS` | Comma-separated allowed frontend origins | `http://localhost:5173,http://127.0.0.1:5173` |
| `MAX_FILE_SIZE` | Maximum file size in bytes | `15728640` (15 MB) |

### Start the Backend

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- Backend API: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

## 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

- Frontend URL: `http://localhost:5173`
- Set `VITE_API_URL` in `.env` or environment to point to custom backend location (defaults to `http://127.0.0.1:8000`).

## 3. Running Tests

```bash
cd backend
pytest -v
```

## Supported Evidence & Analyses

- **Visual Evidence (Content Stream Manipulation)**: Annotates detected stream overlays and text replacements with highlighted regions in generated PDF evidence.
- **Error Level Analysis (ELA)**: Re-compression difference maps for images and PDF pages.
- **Visual Region Analysis**: Font size variations, baseline deviations, color anomalies, and text/image overlaps.
- **PDF Structure & Revisions**: Incremental update inspection, XRef/Prev chains, and linearization checks.
- **Provenance & AI Content**: C2PA manifest parsing, cryptographic signature validation, and generator identification.


## Single-document editing evidence

Upload one submitted PDF and select **Manipulation analysis**. General screening
is independent of ticket extraction and issuer names. Red outlines locate these
supported observations in PDFs of any subject:

- Empty text blocks sharing a position with rendered text. Operator parsing
  supports transformed text, different font resources, combined streams and
  nested Form XObjects.
- Text covered by a later opaque rectangular fill. Painting order excludes
  ordinary backgrounds drawn before the text and translucent highlights.
- FreeText and pending Redact annotations, with their recorded bounds.
- Text changes in the preceding incremental revision retained inside the uploaded
  PDF itself. Page object identity and geometry must agree. Removed text is marked
  at its earlier position, labelled in the report.

Each observation includes a page and bounds. The report links findings to the
corresponding page of the highlighted PDF. Amber outlines remain separate layout
heuristics. Intentional masking, annotations or layout can trigger these rules
and should be reviewed. No reference upload is required or available.

`TEXT_POSITION_TOLERANCE` defaults to 2 PDF points and controls empty-block
position matching (allowed range above 0 through 20). `TEXT_COVERAGE_THRESHOLD`
defaults to 0.9 and controls the fraction of a character covered by an opaque
rectangle (allowed range above 0 through 1). These are explainable geometric
screening thresholds, not calibrated probabilities. Their effective values are
returned in the content-stream results. `FINORA_DATA_DIR` optionally controls the
parent directory for uploads and generated results.

A single file cannot expose every possible edit. A fully regenerated or flattened
PDF can discard earlier text, history and editing operators. Scanned images have
no native text operators for these checks. Those cases may have no locatable
editing evidence. FINORA reports available indicators and does not certify an
unedited file when no matching trace remains.

Run focused tests from the repository root:

```bash
PYTHONPATH=backend python -B -m unittest discover -s backend/tests -v
```

The tests generate synthetic PDFs in temporary directories. They require runtime
PDF/API dependencies plus `httpx` for the in-process API client. Cases cover train,
bus, flight, invoice and letter content, unchanged files, paint-order controls,
transforms, rotated/cropped pages, forms, annotations, retained revisions, full
removal without retained history, evidence rendering and partial failures.
