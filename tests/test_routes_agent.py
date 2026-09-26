import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.database_service import db, now_iso
from app.services.adk_client import adk_client
from app.routes.agent import build_clean_document_context

@pytest.mark.asyncio
async def test_build_clean_document_context_all_branches(tmp_path):
    # 1. No documents
    texts, pdfs = await build_clean_document_context("missing-session")
    assert texts == []
    assert pdfs == []

    # 2. Document missing in DB
    await db.save_session({"id": "s-ctx", "user_id": "u", "document_ids": ["nonexistent-doc"]})
    t2, p2 = await build_clean_document_context("s-ctx")
    assert t2 == []
    assert p2 == []

    # 3. Clean PDF document
    await db.save_document_metadata({
        "id": "doc-pdf-clean",
        "filename": "agreement.pdf",
        "original_filename": "agreement.pdf",
        "content_type": "application/pdf",
        "size_bytes": 100,
        "gcs_uri": "gs://bucket/agreement.pdf",
        "gcs_bucket": "bucket",
        "gcs_path": "uploads/agreement.pdf",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "Valid legal text snippet for testing.",
        "custom_metadata": {}
    })
    t3, p3 = await build_clean_document_context("s-ctx", requested_doc_ids=["doc-pdf-clean"])
    assert len(t3) == 1
    assert "Valid legal text snippet" in t3[0]
    assert p3 == ["gs://bucket/agreement.pdf"]

    # 4. Corrupt binary snippet (starts with PK) -> fresh snippet from storage
    fresh_file = tmp_path / "fresh.txt"
    fresh_file.write_text("Freshly recovered text from docx.", encoding="utf-8")
    await db.save_document_metadata({
        "id": "doc-corrupt-pk",
        "filename": "contract.docx",
        "original_filename": "contract.docx",
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size_bytes": 100,
        "gcs_uri": "file://" + str(fresh_file),
        "gcs_bucket": "b",
        "gcs_path": str(fresh_file),
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "PK\x03\x04corrupted binary stream",
        "custom_metadata": {}
    })
    t4, _ = await build_clean_document_context("s-ctx", requested_doc_ids=["doc-corrupt-pk"])
    assert len(t4) == 1
    assert "Freshly recovered text" in t4[0]

    # 5. Corrupt binary snippet where fresh snippet also fails -> falls back to structured analysis
    analysis_struct = {
        "nature_of_document": {"category": "Corporate", "governing_law": "California"},
        "legal_case_summary": {"plain_verdict": "Standard NDA"},
        "key_clauses": [{"name": "Confidentiality", "verbatim_quote": "Keep secret", "analysis": "Strict"}],
        "risks_and_inconsistencies": [{"severity": "HIGH", "issue": "Uncapped liability", "redline_recommendation": "Cap it"}],
        "deadlines": [{"type": "Notice", "timeframe": "30 days", "description": "Prior notice"}]
    }
    await db.save_document_metadata({
        "id": "doc-unrecoverable",
        "filename": "locked.docx",
        "original_filename": "locked.docx",
        "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size_bytes": 100,
        "gcs_uri": "file:///bad_path",
        "gcs_bucket": "b",
        "gcs_path": "/bad_path",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "PK\x03\x04unrecoverable",
        "custom_metadata": {"analysis": analysis_struct}
    })
    t5, _ = await build_clean_document_context("s-ctx", requested_doc_ids=["doc-unrecoverable"])
    assert len(t5) == 1
    assert "Nature: Corporate" in t5[0]
    assert "Confidentiality" in t5[0]
    assert "Uncapped liability" in t5[0]

@pytest.mark.asyncio
async def test_query_agent_endpoint(async_client):
    # 1. Query with non-existent session (auto-creates session)
    mock_events = [
        {"author": "orchestrator_agent", "content": {"parts": [{"text": "Hello client!"}]}}
    ]
    with patch.object(adk_client, "create_adk_session", new_callable=AsyncMock), \
         patch.object(adk_client, "run_agent", new_callable=AsyncMock, return_value=mock_events):
        resp = await async_client.post("/api/v1/agent/query", json={
            "session_id": "new-sess-1",
            "prompt": "Hello"
        })
        assert resp.status_code == 200
        assert resp.json()["response_text"] == "Hello client!"
        assert resp.json()["agent_name"] == "orchestrator_agent"

    # 2. Query with dict adk_response and empty text fallback
    with patch.object(adk_client, "create_adk_session", new_callable=AsyncMock), \
         patch.object(adk_client, "run_agent", new_callable=AsyncMock, return_value={"author": "specialist_agent", "content": {}}):
        resp2 = await async_client.post("/api/v1/agent/query", json={
            "session_id": "new-sess-1",
            "prompt": "Help"
        })
        assert resp2.status_code == 200
        assert "Analysis completed" in resp2.json()["response_text"]

    # 3. Query with ADK error -> 502 Bad Gateway
    with patch.object(adk_client, "create_adk_session", new_callable=AsyncMock), \
         patch.object(adk_client, "run_agent", side_effect=Exception("Connection refused")):
        resp_err = await async_client.post("/api/v1/agent/query", json={
            "session_id": "new-sess-1",
            "prompt": "Test error"
        })
        assert resp_err.status_code == 502
        assert "ADK Agent Server error" in resp_err.json()["detail"]

    # 4. Query with attached document context
    await db.save_document_metadata({
        "id": "doc-attached",
        "filename": "f.txt",
        "original_filename": "f.txt",
        "content_type": "text/plain",
        "size_bytes": 10,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "p",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "Contractual payment clause: $500/hr."
    })
    with patch.object(adk_client, "create_adk_session", new_callable=AsyncMock), \
         patch.object(adk_client, "run_agent", new_callable=AsyncMock, return_value=mock_events) as mock_run:
        resp_doc = await async_client.post("/api/v1/agent/query", json={
            "session_id": "new-sess-1",
            "prompt": "What is the fee?",
            "document_ids": ["doc-attached"]
        })
        assert resp_doc.status_code == 200
        prompt_arg = mock_run.call_args[1]["prompt_text"]
        assert "Contractual payment clause" in prompt_arg
        assert "What is the fee?" in prompt_arg

@pytest.mark.asyncio
async def test_query_agent_stream_endpoint(async_client):
    # 1. Stream success
    async def mock_stream_gen(*args, **kwargs):
        yield "data: token 1\n\n"
        yield "data: token 2\n\n"

    with patch.object(adk_client, "run_agent_stream", side_effect=mock_stream_gen):
        resp = await async_client.post("/api/v1/agent/query/stream", json={
            "session_id": "stream-sess",
            "prompt": "Stream this"
        })
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        body = resp.text
        assert "token 1" in body
        assert "token 2" in body

    # 2. Stream with exception
    async def mock_stream_err(*args, **kwargs):
        raise Exception("Stream aborted")
        yield "never"

    with patch.object(adk_client, "run_agent_stream", side_effect=mock_stream_err):
        resp_err = await async_client.post("/api/v1/agent/query/stream", json={
            "session_id": "stream-sess",
            "prompt": "Fail stream"
        })
        assert resp_err.status_code == 200
        assert "Stream aborted" in resp_err.text

@pytest.mark.asyncio
async def test_agent_routes_additional_branches(async_client):
    # 1. Fallback to session state analysis in build_clean_document_context (line 54)
    state_analysis = {
        "nature_of_document": {"category": "Real Estate"},
        "legal_case_summary": {"plain_verdict": "Lease Verdict"},
        "key_clauses": [{"name": "Rent", "verbatim_quote": "$1000", "analysis": "Standard"}],
        "risks_and_inconsistencies": [],
        "deadlines": []
    }
    await db.save_session({"id": "s-state-an", "user_id": "u", "state": {"analysis": state_analysis}})
    await db.save_document_metadata({
        "id": "doc-no-meta-an",
        "filename": "lease.docx",
        "original_filename": "lease.docx",
        "content_type": "text/plain",
        "size_bytes": 10,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "p",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "PK\x03\x04corrupted",
        "custom_metadata": {}
    })
    txts, _ = await build_clean_document_context("s-state-an", requested_doc_ids=["doc-no-meta-an"])
    assert len(txts) == 1
    assert "Nature: Real Estate" in txts[0]

    # 2. Query agent with adk sync exception (lines 123-124)
    with patch.object(adk_client, "create_adk_session", side_effect=Exception("ADK session sync err")), \
         patch.object(adk_client, "run_agent", new_callable=AsyncMock, return_value=[{"content": {"parts": [{"text": "OK"}]}}]):
        resp = await async_client.post("/api/v1/agent/query", json={
            "session_id": "s-sync-err",
            "prompt": "Test"
        })
        assert resp.status_code == 200
        assert resp.json()["response_text"] == "OK"

    # 3. Query agent with dict response and parts text (lines 186-187)
    with patch.object(adk_client, "create_adk_session", new_callable=AsyncMock), \
         patch.object(adk_client, "run_agent", new_callable=AsyncMock, return_value={"author": "dict_agent", "content": {"parts": [{"text": "From dict response"}]}}):
        resp_dict = await async_client.post("/api/v1/agent/query", json={
            "session_id": "s-dict-resp",
            "prompt": "Hello"
        })
        assert resp_dict.status_code == 200
        assert resp_dict.json()["response_text"] == "From dict response"
        assert resp_dict.json()["agent_name"] == "dict_agent"

    # 4. Stream query with attached document (line 228)
    async def mock_stream_docs(*args, **kwargs):
        yield "data: stream with doc text\n\n"

    # Save a document with clean snippet
    await db.save_document_metadata({
        "id": "doc-clean-stream",
        "filename": "stream_doc.txt",
        "original_filename": "stream_doc.txt",
        "content_type": "text/plain",
        "size_bytes": 10,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "p",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "Contract clause governing stream analysis."
    })
    with patch.object(adk_client, "run_agent_stream", side_effect=mock_stream_docs) as mock_s:
        resp_s = await async_client.post("/api/v1/agent/query/stream", json={
            "session_id": "s-dict-resp",
            "prompt": "Analyze",
            "document_ids": ["doc-clean-stream"]
        })
        assert resp_s.status_code == 200
        assert "stream with doc text" in resp_s.text

