from __future__ import annotations
import shutil
import tempfile
from pathlib import Path
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from services.contract_parser import extract_contract_text, extract_key_clauses, extract_contract_metadata
from services.erp_parser import load_erp
from services.invoice_parser import load_invoice
from services.payable_engine import analyze_payable


app = FastAPI(title="Account Payables Copilot API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _persist_upload(tmpdir: str, upload: UploadFile) -> str:
    path = Path(tmpdir) / upload.filename
    with path.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return str(path)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze")
async def analyze(
    contract_file: UploadFile = File(...),
    erp_file: UploadFile = File(...),
    invoice_file: UploadFile = File(...),
):
    with tempfile.TemporaryDirectory() as tmpdir:
        contract_path = _persist_upload(tmpdir, contract_file)
        erp_path = _persist_upload(tmpdir, erp_file)
        invoice_path = _persist_upload(tmpdir, invoice_file)

        contract_text = extract_contract_text(contract_path)
        clauses = extract_key_clauses(contract_text)
        contract_meta = extract_contract_metadata(contract_text)
        erp = load_erp(erp_path)
        invoice = load_invoice(invoice_path)
        result = analyze_payable(contract_meta, erp, invoice, clauses)
        return JSONResponse(result.model_dump())
