import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from app.config import settings
from app.schemas import SessionCreateRequest, SessionRecord
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
        # Graceful handling if ADK server is starting or standalone
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
    sess = await db.get_session(session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found in database.")
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
