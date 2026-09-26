import pytest
from app.schemas import (
    DocumentMetadata,
    DocumentUploadResponse,
    SessionCreateRequest,
    SessionUpdateRequest,
    SessionRecord,
    QueryAgentRequest,
    AgentResponse
)

def test_document_metadata_and_upload_response():
    doc = DocumentMetadata(
        id="doc-123",
        filename="contract.pdf",
        original_filename="contract.pdf",
        content_type="application/pdf",
        size_bytes=1024,
        gcs_uri="gs://bucket/contract.pdf",
        gcs_bucket="bucket",
        gcs_path="uploads/contract.pdf",
        uploaded_at="2026-09-26T00:00:00Z",
        user_id="user-1",
        extracted_text_snippet="Test snippet",
        custom_metadata={"test_key": "test_val"}
    )
    assert doc.id == "doc-123"
    assert doc.filename == "contract.pdf"
    assert doc.custom_metadata["test_key"] == "test_val"

    resp = DocumentUploadResponse(document=doc)
    assert resp.document.id == "doc-123"
    assert resp.message == "Document successfully uploaded to Google Cloud Storage"

def test_session_create_and_update_requests():
    req = SessionCreateRequest()
    assert req.user_id is None
    assert req.session_id is None
    assert req.title == "Legal Consultation"
    assert req.document_ids == []
    assert req.initial_state == {}

    custom_req = SessionCreateRequest(
        user_id="usr-1",
        session_id="sess-custom",
        title="Custom Title",
        document_ids=["doc-1"],
        initial_state={"step": 1}
    )
    assert custom_req.user_id == "usr-1"
    assert custom_req.session_id == "sess-custom"
    assert custom_req.document_ids == ["doc-1"]

    upd = SessionUpdateRequest(title="New Title", document_ids=["doc-2"], state={"step": 2})
    assert upd.title == "New Title"
    assert upd.document_ids == ["doc-2"]
    assert upd.state == {"step": 2}

def test_session_record_id_and_session_id_mapping():
    # Branch 1: 'id' provided, no 'session_id'
    r1 = SessionRecord(
        id="sess-id-only",
        app_name="legallens",
        user_id="user-1",
        created_at="2026-09-26T00:00:00Z",
        updated_at="2026-09-26T00:00:00Z"
    )
    assert r1.id == "sess-id-only"
    assert r1.session_id == "sess-id-only"

    # Branch 2: 'session_id' provided, no 'id'
    r2 = SessionRecord(
        session_id="sess-key-only",
        app_name="legallens",
        user_id="user-1",
        created_at="2026-09-26T00:00:00Z",
        updated_at="2026-09-26T00:00:00Z"
    )
    assert r2.id == "sess-key-only"
    assert r2.session_id == "sess-key-only"

    # Branch 3: both provided
    r3 = SessionRecord(
        id="id-1",
        session_id="id-1",
        app_name="legallens",
        user_id="user-1",
        title="My Consultation",
        document_ids=["d1"],
        created_at="2026-09-26T00:00:00Z",
        updated_at="2026-09-26T00:00:00Z",
        state={"key": "val"},
        event_count=5,
        adk_synced=True
    )
    assert r3.id == "id-1"
    assert r3.event_count == 5
    assert r3.adk_synced is True

def test_query_agent_models():
    q = QueryAgentRequest(session_id="sess-1", prompt="Analyze clause 5")
    assert q.session_id == "sess-1"
    assert q.prompt == "Analyze clause 5"
    assert q.streaming is False
    assert q.document_ids == []

    resp = AgentResponse(
        session_id="sess-1",
        user_id="user-1",
        response_text="Clause 5 is standard",
        agent_name="orchestrator_agent",
        citations=[{"clause": "5"}],
        raw_events=[{"event": "1"}]
    )
    assert resp.response_text == "Clause 5 is standard"
    assert resp.agent_name == "orchestrator_agent"
    assert len(resp.citations) == 1
    assert len(resp.raw_events) == 1
