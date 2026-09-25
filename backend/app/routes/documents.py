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
    description: Optional[str] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """
    Accepts file upload (PDF/DOCX/TXT/Images), saves to Google Cloud Storage (or fallback),
    records document metadata in database, links to session, stores extracted dashboard breakdown,
    and synchronizes with ADK session memory.
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

    # 3. Dynamically extract structured legal breakdown dashboard elements
    from app.services.analysis_service import analysis_service
    analysis_data = await analysis_service.analyze_document(
        text=snippet or "",
        filename=file.filename or "contract.pdf"
    )

    # 4. Store document metadata with analysis in the database
    doc_id = str(uuid.uuid4())
    custom_meta = {"description": description} if description else {}
    custom_meta["analysis"] = analysis_data

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
        custom_metadata=custom_meta
    )

    await db.save_document_metadata(doc_metadata.dict())

    # 5. Link document and extracted metadata directly to the active consultation session
    if session_id:
        sess = await db.get_session(session_id)
        if sess:
            current_docs = sess.get("document_ids", [])
            if doc_id not in current_docs:
                current_docs.append(doc_id)
            sess["document_ids"] = current_docs

            if "state" not in sess or not isinstance(sess["state"], dict):
                sess["state"] = {}
            sess["state"]["analysis"] = analysis_data
            sess["state"]["dashboard_breakdown"] = analysis_data
            sess["updated_at"] = now_iso()
            await db.save_session(sess)

            # Log intake event in database audit trail for chat reconstruction
            doc_type = (
                analysis_data.get("nature_of_document", {}).get("document_type")
                or analysis_data.get("nature_of_document", {}).get("category")
                or "Legal Agreement"
            )
            verdict = (
                analysis_data.get("legal_case_summary", {}).get("plain_verdict")
                or "Legal document parsed and cataloged."
            )
            risk_count = len(analysis_data.get("risks_and_inconsistencies", []))
            deadline_count = len(analysis_data.get("deadlines", []))

            intake_msg = (
                f"**Analysis Complete:** `{file.filename}` has been parsed and cataloged into this consultation.\n\n"
                f"• **Nature:** {doc_type}\n"
                f"• **Verdict:** {verdict}\n"
                f"• **Key Signals:** Highlighted **{risk_count} risks & inconsistencies** and **{deadline_count} critical deadlines**.\n\n"
                "The central dashboard has been populated with straight-to-the-point answers. Feel free to ask questions below."
            )

            await db.log_session_event(session_id, {
                "type": "agent_response",
                "agent_name": "intake_parser_agent",
                "text": intake_msg,
                "document_ids": [doc_id],
                "user_id": active_user_id
            })

            # Sync ADK session memory
            try:
                from app.services.adk_client import adk_client
                await adk_client.create_adk_session(
                    user_id=active_user_id,
                    session_id=session_id,
                    initial_state=sess["state"]
                )
            except Exception:
                pass

    return DocumentUploadResponse(
        document=doc_metadata,
        message=f"Document '{file.filename}' uploaded and analyzed successfully."
    )

@router.post("/{document_id}/analyze")
async def analyze_document_endpoint(document_id: str):
    """
    Manually triggers or refreshes dynamic legal breakdown analysis for a stored document.
    """
    doc = await db.get_document_metadata(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    from app.services.analysis_service import analysis_service
    text = doc.get("extracted_text_snippet") or ""
    if not text and doc.get("gcs_path"):
        text = storage_service.read_file_text_sample(doc["gcs_path"]) or ""
        doc["extracted_text_snippet"] = text

    analysis = await analysis_service.analyze_document(text, doc.get("original_filename", "contract.pdf"))
    
    if not doc.get("custom_metadata"):
        doc["custom_metadata"] = {}
    doc["custom_metadata"]["analysis"] = analysis
    await db.save_document_metadata(doc)

    return {
        "document_id": document_id,
        "filename": doc.get("original_filename"),
        "analysis": analysis
    }

@router.get("/{document_id}/analysis")
async def get_document_analysis(document_id: str):
    """
    Retrieves the structured breakdown dashboard for a document.
    """
    doc = await db.get_document_metadata(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    custom = doc.get("custom_metadata") or {}
    if "analysis" in custom:
        return {
            "document_id": document_id,
            "filename": doc.get("original_filename"),
            "analysis": custom["analysis"]
        }

    # If not yet analyzed, analyze on-the-fly
    from app.services.analysis_service import analysis_service
    text = doc.get("extracted_text_snippet") or ""
    if not text and doc.get("gcs_path"):
        text = storage_service.read_file_text_sample(doc["gcs_path"]) or ""
        doc["extracted_text_snippet"] = text

    analysis = await analysis_service.analyze_document(text, doc.get("original_filename", "contract.pdf"))
    custom["analysis"] = analysis
    doc["custom_metadata"] = custom
    await db.save_document_metadata(doc)

    return {
        "document_id": document_id,
        "filename": doc.get("original_filename"),
        "analysis": analysis
    }

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
