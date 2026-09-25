import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.config import settings
from app.schemas import QueryAgentRequest, AgentResponse
from app.services.database_service import db, now_iso
from app.services.adk_client import adk_client

router = APIRouter()

@router.post("/query", response_model=AgentResponse)
async def query_agent(request: QueryAgentRequest):
    """
    Submits a query or document instruction to the LegalLens Orchestrator agent via ADK /run.
    Retrieves document GCS URIs for context, logs request & response events in the database.
    """
    user_id = request.user_id or settings.DEFAULT_USER_ID

    # 1. Verify session exists in DB; get session's actual user_id
    session = await db.get_session(request.session_id)
    if session:
        user_id = session.get("user_id") or user_id
    else:
        session_data = {
            "id": request.session_id,
            "app_name": settings.ADK_APP_NAME,
            "user_id": user_id,
            "title": "Legal Consultation",
            "document_ids": request.document_ids or [],
            "created_at": now_iso(),
            "updated_at": now_iso(),
            "state": {},
            "event_count": 0,
            "adk_synced": False
        }
        await db.save_session(session_data)

    # Ensure ADK has registered this session
    try:
        await adk_client.create_adk_session(user_id=user_id, session_id=request.session_id)
    except Exception:
        pass

    # 2. Collect document contents
    text_contexts = []
    if request.document_ids:
        from app.services.storage_service import storage_service
        for doc_id in request.document_ids:
            doc = await db.get_document_metadata(doc_id)
            if doc:
                doc_name = doc.get("original_filename", "Document")
                raw_snippet = doc.get("extracted_text_snippet") or ""
                # If previously stored snippet was empty or binary, re-extract now using pypdf
                if not raw_snippet and doc.get("gcs_path"):
                    raw_snippet = storage_service.read_file_text_sample(doc["gcs_path"]) or ""
                    if raw_snippet:
                        doc["extracted_text_snippet"] = raw_snippet
                        await db.save_document_metadata(doc)

                clean_snippet = " ".join(raw_snippet.split())
                if clean_snippet:
                    text_contexts.append(f"Document [{doc_name}]: {clean_snippet}")

    clean_prompt = " ".join(request.prompt.split())
    if text_contexts:
        final_prompt = " ".join(text_contexts) + f" Question: {clean_prompt}"
    else:
        final_prompt = clean_prompt

    # 3. Log user query event in Database
    await db.log_session_event(request.session_id, {
        "type": "user_query",
        "prompt": request.prompt,
        "document_ids": request.document_ids,
        "user_id": user_id
    })

    # 4. Invoke ADK Server via /run
    try:
        adk_response = await adk_client.run_agent(
            user_id=user_id,
            session_id=request.session_id,
            prompt_text=final_prompt,
            streaming=False,
            state_delta=request.state_delta,
            file_gcs_uris=None
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"ADK Agent Server error: {str(e)}. Ensure 'adk api_server' is running on {settings.ADK_SERVER_URL}."
        )

    # 5. Extract response text and events from ADK response
    # ADK /run returns a list of events or a single event dictionary
    response_text = ""
    active_agent = "orchestrator_agent"
    raw_events = []

    if isinstance(adk_response, list):
        raw_events = adk_response
        for event in adk_response:
            if isinstance(event, dict):
                # Check for agent name
                if "author" in event:
                    active_agent = event.get("author") or active_agent
                # Check for content text
                content = event.get("content") or {}
                parts = content.get("parts", []) if isinstance(content, dict) else []
                for p in parts:
                    if isinstance(p, dict) and p.get("text"):
                        response_text += p["text"]
    elif isinstance(adk_response, dict):
        raw_events = [adk_response]
        content = adk_response.get("content") or {}
        parts = content.get("parts", []) if isinstance(content, dict) else []
        for p in parts:
            if isinstance(p, dict) and p.get("text"):
                response_text += p["text"]

    if not response_text:
        response_text = "Analysis completed. Please check event log."

    # 6. Log Agent Response in Database
    await db.log_session_event(request.session_id, {
        "type": "agent_response",
        "agent_name": active_agent,
        "text": response_text,
        "user_id": user_id
    })

    return AgentResponse(
        session_id=request.session_id,
        user_id=user_id,
        response_text=response_text,
        agent_name=active_agent,
        citations=[],
        raw_events=raw_events
    )

@router.post("/query/stream")
async def query_agent_stream(request: QueryAgentRequest):
    """
    Streams ADK agent response in real time via Server-Sent Events (SSE).
    """
    user_id = request.user_id or settings.DEFAULT_USER_ID

    # Log user query event in DB
    await db.log_session_event(request.session_id, {
        "type": "user_stream_query",
        "prompt": request.prompt,
        "document_ids": request.document_ids
    })

    # Collect document contexts
    text_contexts = []
    gcs_uris = []
    if request.document_ids:
        for doc_id in request.document_ids:
            doc = await db.get_document_metadata(doc_id)
            if doc:
                if doc.get("gcs_uri") and doc["gcs_uri"].startswith("gs://"):
                    gcs_uris.append(doc["gcs_uri"])
                elif doc.get("extracted_text_snippet"):
                    text_contexts.append(f"[Document: {doc['original_filename']}]\n{doc['extracted_text_snippet']}")

    final_prompt = request.prompt
    if text_contexts:
        final_prompt = "\n\n".join(text_contexts) + f"\n\nUser Question:\n{request.prompt}"

    async def sse_generator():
        try:
            async for chunk in adk_client.run_agent_stream(
                user_id=user_id,
                session_id=request.session_id,
                prompt_text=final_prompt,
                state_delta=request.state_delta,
                file_gcs_uris=gcs_uris if gcs_uris else None
            ):
                yield chunk
        except Exception as e:
            err_payload = json.dumps({"error": str(e)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
