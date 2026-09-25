import uuid
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query
from app.config import settings
from app.schemas import DocumentMetadata, DocumentUploadResponse
from app.services.storage_service import storage_service
from app.services.database_service import db, now_iso

router = APIRouter()

ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    "image/png",
    "image/jpeg",
    "image/webp"
}

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: Optional[str] = Form(None),
    description: Optional[str] = Form(None)
):
    """
    Accepts file upload (PDF/DOCX/TXT/Images), saves to Google Cloud Storage (or fallback),
    and records document metadata in the database (Firestore / SQLite).
    """
    active_user_id = user_id or settings.DEFAULT_USER_ID

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # 1. Upload to Google Cloud Storage
    gcs_uri, gcs_path = storage_service.upload_file_bytes(
        file_bytes=content,
        original_filename=file.filename or "uploaded_document",
        content_type=file.content_type or "application/octet-stream",
        user_id=active_user_id
    )

    # 2. Extract text preview if possible
    snippet = storage_service.read_file_text_sample(gcs_path)

    # 3. Store document metadata in the database
    doc_id = str(uuid.uuid4())
    doc_metadata = DocumentMetadata(
        id=doc_id,
        filename=file.filename or "document",
        original_filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        size_bytes=len(content),
        gcs_uri=gcs_uri,
        gcs_bucket=settings.GCS_BUCKET_NAME,
        gcs_path=gcs_path,
        uploaded_at=now_iso(),
        user_id=active_user_id,
        extracted_text_snippet=snippet,
        custom_metadata={"description": description} if description else {}
    )

    await db.save_document_metadata(doc_metadata.dict())

    return DocumentUploadResponse(
        document=doc_metadata,
        message=f"Document '{file.filename}' uploaded successfully to GCS."
    )

@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document(document_id: str):
    doc = await db.get_document_metadata(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentMetadata(**doc)

@router.get("", response_model=List[DocumentMetadata])
async def list_documents(user_id: Optional[str] = Query(None)):
    active_user_id = user_id or settings.DEFAULT_USER_ID
    docs = await db.list_documents(active_user_id)
    return [DocumentMetadata(**d) for d in docs]
