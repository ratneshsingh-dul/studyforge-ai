from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.dependencies import CurrentUser
from app.models import Document, DocumentChunk
from app.services.pdf_processing import extract_pdf_chunks

router = APIRouter(prefix="/api/documents", tags=["documents"])
MAX_UPLOAD_BYTES = get_settings().max_upload_mb * 1024 * 1024


class DocumentPublic(BaseModel):
    id: int
    original_filename: str
    size_bytes: int
    page_count: int
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


@router.get("", response_model=list[DocumentPublic])
def list_documents(user: CurrentUser, db: Session = Depends(get_db)) -> list[Document]:
    return list(
        db.scalars(
            select(Document).where(Document.owner_id == user.id).order_by(Document.created_at.desc())
        )
    )


@router.post("", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED)
async def upload_document(
    user: CurrentUser,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Document:
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="Upload a PDF file")

    pdf_bytes = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"PDFs must be {get_settings().max_upload_mb} MB or smaller")
    try:
        page_count, chunks = extract_pdf_chunks(pdf_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    storage_name = f"{uuid4().hex}.pdf"
    document = Document(
        owner_id=user.id,
        original_filename=filename[:255],
        storage_name=storage_name,
        size_bytes=len(pdf_bytes),
        page_count=page_count,
        status="ready",
    )
    document.chunks = [
        DocumentChunk(page_number=page, chunk_index=index, content=content)
        for page, index, content in chunks
    ]
    storage_dir = Path(get_settings().upload_dir) / str(user.id)
    storage_dir.mkdir(parents=True, exist_ok=True)
    stored_path = storage_dir / storage_name
    try:
        stored_path.write_bytes(pdf_bytes)
        db.add(document)
        db.commit()
        db.refresh(document)
    except Exception:
        db.rollback()
        stored_path.unlink(missing_ok=True)
        raise
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, user: CurrentUser, db: Session = Depends(get_db)) -> None:
    document = db.scalar(
        select(Document).where(Document.id == document_id, Document.owner_id == user.id)
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    stored_path = Path(get_settings().upload_dir) / str(user.id) / document.storage_name
    db.delete(document)
    db.commit()
    stored_path.unlink(missing_ok=True)
