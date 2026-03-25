"""
RAG Policy Store admin endpoint.
Single endpoint: upload a PDF (or .txt/.md) to inject into the policy store.
"""
import os
import tempfile
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends
from fastapi.security import APIKeyHeader

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rag-policy-store", tags=["rag-policy-store"])


@router.post("/upload")
async def upload_policy(
    file: UploadFile = File(...),
    section_title: Optional[str] = None,
):
    """
    Upload a PDF, .txt, or .md file to inject its contents as a new policy
    section into the ChromaDB RAG policy store.
    """
    allowed = {".pdf", ".txt", ".md"}
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Allowed: pdf, txt, md"
        )

    try:
        raw = await file.read()

        if suffix == ".pdf":
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(raw)
                tmp_path = tmp.name
            try:
                from app.services.pdf_extractor import PDFExtractor
                text = await PDFExtractor.extract_text(tmp_path)
            finally:
                os.unlink(tmp_path)
        else:
            text = raw.decode("utf-8", errors="ignore")

        if not text.strip():
            raise HTTPException(status_code=422, detail="No extractable text found in the uploaded file")

        title = section_title or f"Uploaded: {file.filename}"
        from app.services.rag import PolicyStore
        store = PolicyStore()
        total = store.add_policy(section_title=title, policy_text=text[:8000])

        return {
            "status": "ok",
            "filename": file.filename,
            "section": title,
            "extracted_chars": len(text),
            "total_chunks": total,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Policy upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
