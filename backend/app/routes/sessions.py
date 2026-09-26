import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from app.config import settings
from app.schemas import SessionCreateRequest, SessionUpdateRequest, SessionRecord
from app.services.database_service import db, now_iso
from app.services.adk_client import adk_client

router = APIRouter()

@router.post("", response_model=SessionRecord)
async def create_session(request: SessionCreateRequest):
    """
    Creates a new legal consultation session, saves it to the database,
    and synchronizes it with the ADK server via POST /apps/{app_name}/users/{user_id}/sessions.
    """
    user_id = request.user_id or settings.DEFAULT_USER_ID
    session_id = request.session_id or f"session-{uuid.uuid4().hex[:12]}"
    title = request.title or "Legal Consultation"

    # 1. Create session in ADK server if reachable
    adk_synced = False
    try:
        await adk_client.create_adk_session(
            user_id=user_id,
            session_id=session_id,
            initial_state=request.initial_state
        )
        adk_synced = True
    except Exception as e:
        pass

    # 2. Persist session record in Database (Firestore / SQLite)
    session_record = SessionRecord(
        id=session_id,
        app_name=settings.ADK_APP_NAME,
        user_id=user_id,
        title=title,
        document_ids=request.document_ids or [],
        created_at=now_iso(),
        updated_at=now_iso(),
        state=request.initial_state or {},
        event_count=0,
        adk_synced=adk_synced
    )

    await db.save_session(session_record.dict())
    return session_record

@router.get("/{session_id}", response_model=SessionRecord)
async def get_session(session_id: str):
    """
    Fetches session details from database and synchronizes/maps with Google ADK session memory.
    """
    sess = await db.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found in database.")

    user_id = sess.get("user_id", settings.DEFAULT_USER_ID)

    # Map with ADK Session Memory:
    # Check if ADK server already holds this session; if not or if restarted, re-seed ADK memory
    try:
        adk_sess = await adk_client.get_adk_session(user_id=user_id, session_id=session_id)
        if not adk_sess:
            # Re-seed session into ADK with existing DB state
            await adk_client.create_adk_session(
                user_id=user_id,
                session_id=session_id,
                initial_state=sess.get("state", {})
            )
            sess["adk_synced"] = True
        else:
            # Sync ADK session memory/state back to database
            adk_state = adk_sess.get("state") or {}
            if adk_state and adk_state != sess.get("state"):
                sess["state"].update(adk_state)
                await db.update_session_state(session_id, adk_state)
            sess["adk_synced"] = True
    except Exception:
        sess["adk_synced"] = False

    return SessionRecord(**sess)

@router.patch("/{session_id}", response_model=SessionRecord)
@router.put("/{session_id}", response_model=SessionRecord)
async def update_session(session_id: str, request: SessionUpdateRequest):
    """
    Renames the consultation title and/or updates attached document IDs and state in the database,
    synchronizing updates with ADK session memory.
    """
    sess = await db.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found in database.")

    user_id = sess.get("user_id", settings.DEFAULT_USER_ID)

    if request.title is not None and request.title.strip():
        sess["title"] = request.title.strip()
        await db.update_session_title(session_id, sess["title"])

    if request.document_ids is not None:
        sess["document_ids"] = request.document_ids

    if request.state is not None:
        sess["state"].update(request.state)
        await db.update_session_state(session_id, request.state)

    sess["updated_at"] = now_iso()
    await db.save_session(sess)

    # Sync title & metadata to ADK session memory if possible
    try:
        await adk_client.create_adk_session(
            user_id=user_id,
            session_id=session_id,
            initial_state={"consultation_title": sess["title"], **sess.get("state", {})}
        )
        sess["adk_synced"] = True
    except Exception:
        pass

    return SessionRecord(**sess)

@router.get("", response_model=List[SessionRecord])
async def list_sessions(user_id: Optional[str] = Query(None)):
    active_user_id = user_id or settings.DEFAULT_USER_ID
    sessions = await db.list_sessions(active_user_id)
    return [SessionRecord(**s) for s in sessions]

@router.get("/{session_id}/events")
async def get_session_events(session_id: str):
    """Returns the chronological audit trail and events stored for this session."""
    events = await db.get_session_events(session_id)
    return {"session_id": session_id, "events": events}

@router.delete("/{session_id}")
async def delete_session(session_id: str, user_id: Optional[str] = Query(None)):
    """
    Deletes a consultation session and its events from the database,
    and removes it from the ADK server if active.
    """
    active_user_id = user_id or settings.DEFAULT_USER_ID
    
    # 1. Best-effort deletion in ADK server
    try:
        await adk_client.delete_adk_session(active_user_id, session_id)
    except Exception:
        pass

    # 2. Delete from database
    deleted = await db.delete_session(session_id)
    return {
        "status": "success",
        "session_id": session_id,
        "deleted": deleted
    }

@router.get("/{session_id}/dashboard")
async def get_session_dashboard(session_id: str):
    """
    Returns the structured breakdown dashboard for the active consultation session.
    Aggregates or fetches analysis for attached documents.
    """
    sess = await db.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    doc_ids = sess.get("document_ids", [])
    if not doc_ids:
        # Check if stored in session state
        state = sess.get("state") or {}
        if "analysis" in state:
            return {"session_id": session_id, "has_document": True, "analysis": state["analysis"]}
        return {
            "session_id": session_id,
            "has_document": False,
            "message": "No legal document attached yet to this consultation.",
            "analysis": None
        }

    # Retrieve first/primary document's analysis
    from app.services.analysis_service import analysis_service
    from app.services.storage_service import storage_service

    primary_doc_id = doc_ids[0]
    doc = await db.get_document_metadata(primary_doc_id)
    if not doc:
        state = sess.get("state") or {}
        if "analysis" in state:
            return {"session_id": session_id, "has_document": True, "analysis": state["analysis"]}
        return {"session_id": session_id, "has_document": False, "analysis": None}

    custom = doc.get("custom_metadata") or {}
    if "analysis" in custom:
        return {
            "session_id": session_id,
            "has_document": True,
            "document": doc,
            "analysis": custom["analysis"]
        }

    # Check if session state holds cached analysis
    state = sess.get("state") or {}
    if "analysis" in state:
        custom["analysis"] = state["analysis"]
        doc["custom_metadata"] = custom
        await db.save_document_metadata(doc)
        return {
            "session_id": session_id,
            "has_document": True,
            "document": doc,
            "analysis": state["analysis"]
        }

    # Run analysis if not yet cached
    text = doc.get("extracted_text_snippet") or ""
    if not text and doc.get("gcs_path"):
        text = storage_service.read_file_text_sample(doc["gcs_path"]) or ""
        doc["extracted_text_snippet"] = text

    analysis = await analysis_service.analyze_document(text, doc.get("original_filename", "document.pdf"))
    custom["analysis"] = analysis
    doc["custom_metadata"] = custom
    await db.save_document_metadata(doc)

    if "state" not in sess or not isinstance(sess["state"], dict):
        sess["state"] = {}
    sess["state"]["analysis"] = analysis
    sess["state"]["dashboard_breakdown"] = analysis
    sess["updated_at"] = now_iso()
    await db.update_session_state(session_id, sess["state"])
    await db.save_session(sess)

    return {
        "session_id": session_id,
        "has_document": True,
        "document": doc,
        "analysis": analysis
    }

@router.post("/{session_id}/analyze")
async def analyze_session(session_id: str):
    """
    Forces dynamic re-analysis of documents attached to the session.
    """
    sess = await db.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found.")

    doc_ids = sess.get("document_ids", [])
    if not doc_ids:
        raise HTTPException(status_code=400, detail="Cannot analyze consultation without attached documents.")

    from app.services.analysis_service import analysis_service
    from app.services.storage_service import storage_service

    primary_doc_id = doc_ids[0]
    doc = await db.get_document_metadata(primary_doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    text = doc.get("extracted_text_snippet") or ""
    raw_bytes = None
    if doc.get("gcs_path"):
        raw_bytes = storage_service.get_file_bytes(doc["gcs_path"])
        if not text:
            text = storage_service.read_file_text_sample(doc["gcs_path"]) or ""
            doc["extracted_text_snippet"] = text

    analysis = await analysis_service.analyze_document(
        text=text,
        filename=doc.get("original_filename", "document.pdf"),
        raw_bytes=raw_bytes,
        mime_type=doc.get("content_type", "application/pdf")
    )

    if (not text or len(text.strip()) < 20) and analysis:
        sum_text = analysis.get("legal_case", {}).get("straightforward_summary")
        if sum_text and "processing" not in sum_text.lower():
            doc["extracted_text_snippet"] = f"Document: {doc.get('original_filename')}\nSummary: {sum_text}"

    if not doc.get("custom_metadata"):
        doc["custom_metadata"] = {}
    doc["custom_metadata"]["analysis"] = analysis
    await db.save_document_metadata(doc)

    # Also persist breakdown in consultation session state and sync with ADK memory
    if "state" not in sess or not isinstance(sess["state"], dict):
        sess["state"] = {}
    sess["state"]["analysis"] = analysis
    sess["state"]["dashboard_breakdown"] = analysis
    sess["updated_at"] = now_iso()
    await db.update_session_state(session_id, sess["state"])
    await db.save_session(sess)

    try:
        user_id = sess.get("user_id", settings.DEFAULT_USER_ID)
        await adk_client.create_adk_session(
            user_id=user_id,
            session_id=session_id,
            initial_state=sess["state"]
        )
    except Exception:
        pass

    return {
        "session_id": session_id,
        "document_id": primary_doc_id,
        "filename": doc.get("original_filename"),
        "analysis": analysis
    }

@router.post("/{session_id}/dashboard")
@router.put("/{session_id}/dashboard")
async def save_session_dashboard(session_id: str, dashboard_data: Dict[str, Any]):
    """
    Saves or overrides structured breakdown dashboard details directly in the consultation database record
    and synchronizes it into ADK session state memory.
    """
    sess = await db.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found in database.")

    if "state" not in sess or not isinstance(sess["state"], dict):
        sess["state"] = {}

    analysis_data = dashboard_data.get("analysis", dashboard_data)
    sess["state"]["analysis"] = analysis_data
    sess["state"]["dashboard_breakdown"] = analysis_data
    sess["updated_at"] = now_iso()

    await db.update_session_state(session_id, sess["state"])
    await db.save_session(sess)

    # Sync into ADK session state memory
    try:
        user_id = sess.get("user_id", settings.DEFAULT_USER_ID)
        await adk_client.create_adk_session(
            user_id=user_id,
            session_id=session_id,
            initial_state=sess["state"]
        )
    except Exception:
        pass

    return {
        "status": "success",
        "message": "Dashboard breakdown successfully stored in database and synced to ADK session memory",
        "session_id": session_id,
        "analysis": analysis_data
    }

