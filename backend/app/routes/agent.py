import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.config import settings
from app.schemas import QueryAgentRequest, AgentResponse
from app.services.database_service import db, now_iso
from app.services.adk_client import adk_client

router = APIRouter()

async def build_clean_document_context(session_id: str, requested_doc_ids: Optional[List[str]] = None) -> tuple[List[str], List[str]]:
    """
    Retrieves clean, readable text context for attached documents,
    ensuring DOCX OpenXML / PDF text is properly parsed and NEVER passing
    raw PK/binary compressed data to the ADK agent.
    Returns (text_contexts, valid_pdf_gcs_uris).
    """
    from app.services.storage_service import storage_service
    session = await db.get_session(session_id)
    doc_ids = requested_doc_ids or (session.get("document_ids", []) if session else [])

    text_contexts = []
    pdf_gcs_uris = []

    for doc_id in doc_ids:
        doc = await db.get_document_metadata(doc_id)
        if not doc:
            continue

        doc_name = doc.get("original_filename", "Document")
        raw_snippet = doc.get("extracted_text_snippet") or ""

        # Check if snippet is missing or contains binary/PK compression junk
        is_corrupt_binary = (
            not raw_snippet 
            or raw_snippet.startswith("PK") 
            or "\x00" in raw_snippet[:100]
            or raw_snippet.strip().startswith("PK\x03\x04")
        )

        if is_corrupt_binary and doc.get("gcs_path"):
            fresh_snippet = storage_service.read_file_text_sample(doc["gcs_path"]) or ""
            if fresh_snippet and not fresh_snippet.startswith("PK") and "\x00" not in fresh_snippet[:100]:
                raw_snippet = fresh_snippet
                doc["extracted_text_snippet"] = fresh_snippet
                await db.save_document_metadata(doc)

        # If snippet is still unreadable or binary, fall back to structured analysis summary
        if not raw_snippet or raw_snippet.startswith("PK") or "\x00" in raw_snippet[:100]:
            custom = doc.get("custom_metadata") or {}
            analysis = custom.get("analysis")
            if not analysis and session:
                analysis = session.get("state", {}).get("analysis")
            
            if analysis:
                nature = analysis.get("nature_of_document", {})
                summary = analysis.get("legal_case_summary", {})
                clauses = analysis.get("key_clauses", [])
                risks = analysis.get("risks_and_inconsistencies", [])
                deadlines = analysis.get("deadlines", [])

                summary_parts = [
                    f"Document: {doc_name}",
                    f"Nature: {nature.get('category') or nature.get('document_type', 'Legal Agreement')}",
                    f"Governing Law: {nature.get('governing_law', 'Not specified')}",
                    f"Verdict: {summary.get('plain_verdict', 'N/A')}",
                ]
                if clauses:
                    summary_parts.append("Key Clauses:")
                    for c in clauses[:5]:
                        summary_parts.append(f"- {c.get('name')}: {c.get('verbatim_quote', '')} ({c.get('analysis', '')})")
                if risks:
                    summary_parts.append("Flagged Risks:")
                    for r in risks[:5]:
                        summary_parts.append(f"- [{r.get('severity')}] {r.get('issue')}: {r.get('redline_recommendation', '')}")
                if deadlines:
                    summary_parts.append("Key Deadlines:")
                    for d in deadlines[:5]:
                        summary_parts.append(f"- {d.get('type')}: {d.get('timeframe')} ({d.get('description', '')})")
                raw_snippet = "\n".join(summary_parts)

        clean_snippet = " ".join(raw_snippet.split())
        if clean_snippet and not clean_snippet.startswith("PK"):
            text_contexts.append(f"Document [{doc_name}]:\n{clean_snippet}")

        # Only pass GCS URI directly if it is a confirmed PDF (NOT docx / zip)
        if doc.get("content_type") == "application/pdf" and doc.get("gcs_uri", "").startswith("gs://"):
            pdf_gcs_uris.append(doc["gcs_uri"])

    return text_contexts, pdf_gcs_uris

@router.post("/query", response_model=AgentResponse)
async def query_agent(request: QueryAgentRequest):
    """
    Submits a query or document instruction to the LegalLens Orchestrator agent via ADK /run.
    Retrieves document context cleanly, logs request & response events in the database.
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

    # 2. Collect clean document contents (never raw PK-compressed bytes)
    text_contexts, pdf_gcs_uris = await build_clean_document_context(request.session_id, request.document_ids)

    clean_prompt = request.prompt.strip()
    if text_contexts:
        final_prompt = (
            "Here is the text content of the legal document(s) for this consultation:\n\n"
            + "\n\n---\n\n".join(text_contexts)
            + f"\n\nUser Question:\n{clean_prompt}"
        )
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
            file_gcs_uris=pdf_gcs_uris if pdf_gcs_uris else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=502,
            detail=f"ADK Agent Server error: {str(e)}. Ensure 'adk api_server' is running on {settings.ADK_SERVER_URL}."
        )

    # 5. Extract response text and events from ADK response
    response_text = ""
    active_agent = "orchestrator_agent"
    raw_events = []

    if isinstance(adk_response, list):
        raw_events = adk_response
        for event in adk_response:
            if isinstance(event, dict):
                if "author" in event:
                    active_agent = event.get("author") or active_agent
                content = event.get("content") or {}
                parts = content.get("parts", []) if isinstance(content, dict) else []
                for p in parts:
                    if isinstance(p, dict) and p.get("text"):
                        response_text += p["text"]
    elif isinstance(adk_response, dict):
        raw_events = [adk_response]
        if "author" in adk_response:
            active_agent = adk_response.get("author") or active_agent
        content = adk_response.get("content") or {}
        parts = content.get("parts", []) if isinstance(content, dict) else []
        for p in parts:
            if isinstance(p, dict) and p.get("text"):
                response_text += p["text"]

    if not response_text:
        response_text = "Analysis completed. Please check consultation dashboard for structured breakdown."

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

    # Collect clean document contexts
    text_contexts, pdf_gcs_uris = await build_clean_document_context(request.session_id, request.document_ids)

    clean_prompt = request.prompt.strip()
    if text_contexts:
        final_prompt = (
            "Here is the text content of the legal document(s) for this consultation:\n\n"
            + "\n\n---\n\n".join(text_contexts)
            + f"\n\nUser Question:\n{clean_prompt}"
        )
    else:
        final_prompt = clean_prompt

    async def sse_generator():
        accumulated_text = ""
        try:
            async for chunk in adk_client.run_agent_stream(
                user_id=user_id,
                session_id=request.session_id,
                prompt_text=final_prompt,
                state_delta=request.state_delta,
                file_gcs_uris=pdf_gcs_uris if pdf_gcs_uris else None
            ):
                accumulated_text += chunk
                yield chunk

            # Log stream completion event in database
            if accumulated_text:
                await db.log_session_event(request.session_id, {
                    "type": "agent_response",
                    "agent_name": "orchestrator_agent",
                    "text": accumulated_text,
                    "user_id": user_id
                })
        except Exception as e:
            err_payload = json.dumps({"error": str(e)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")
