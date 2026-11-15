# Digital Document Forensics — Day 1 Starter

A minimal React + FastAPI starter for the 7-day project.

## Requirements
- Python 3.10+
- Node.js 18+
- npm

## 1. Start the backend

```bash
cd backend
python -m venv .venv
```

Activate the environment:

**Windows PowerShell**
```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install and run:
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend: http://127.0.0.1:8000  
API docs: http://127.0.0.1:8000/docs

## 2. Start the frontend

Open a second terminal:
```bash
cd frontend
npm install
npm run dev
```

Open the local URL printed by Vite (usually http://localhost:5173).

## 3. Day 1 acceptance checklist
- [ ] Backend starts without errors.
- [ ] Frontend starts without errors.
- [ ] Upload a valid JPG, PNG or PDF.
- [ ] Backend returns a file ID, file type and size.
- [ ] Unsupported files (e.g. .txt) are rejected.
- [ ] Files larger than 15 MB are rejected.

## Important
This is only the upload foundation. It does **not** yet determine whether a document is genuine or manipulated. Detection modules will be added after the upload and preprocessing pipeline is stable.
