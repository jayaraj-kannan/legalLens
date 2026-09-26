import io
import pytest
from unittest.mock import AsyncMock, patch
from app.services.database_service import db, now_iso
from app.services.adk_client import adk_client

@pytest.mark.asyncio
async def test_upload_document_endpoint(async_client):
    # 1. Empty file -> 400 Bad Request
    files_empty = {"file": ("empty.txt", b"", "text/plain")}
    resp_empty = await async_client.post("/api/v1/documents/upload", files=files_empty)
    assert resp_empty.status_code == 400
    assert "Uploaded file is empty" in resp_empty.json()["detail"]

    # 2. Upload valid file without session_id
    files_valid = {"file": ("nda.txt", b"Mutual NDA Agreement between Company A and Company B.", "text/plain")}
    data = {"description": "Sample NDA test"}
    resp_valid = await async_client.post("/api/v1/documents/upload", files=files_valid, data=data)
    assert resp_valid.status_code == 200
    doc_data = resp_valid.json()["document"]
    assert doc_data["filename"] == "nda.txt"
    assert doc_data["custom_metadata"]["description"] == "Sample NDA test"
    assert "analysis" in doc_data["custom_metadata"]

    # 3. Upload valid file with session_id (session exists, ADK sync success)
    await db.save_session({"id": "s-attach-doc", "user_id": "u", "document_ids": []})
    with patch.object(adk_client, "create_adk_session", new_callable=AsyncMock) as mock_adk:
        files_sess = {"file": ("lease.pdf", b"%PDF-1.4 lease text", "application/pdf")}
        data_sess = {"session_id": "s-attach-doc"}
        resp_sess = await async_client.post("/api/v1/documents/upload", files=files_sess, data=data_sess)
        assert resp_sess.status_code == 200
        mock_adk.assert_called_once()
        
        # Verify session was updated with doc_id
        updated_s = await db.get_session("s-attach-doc")
        assert len(updated_s["document_ids"]) == 1

    # 4. Upload with session_id when ADK sync throws exception
    with patch.object(adk_client, "create_adk_session", side_effect=Exception("ADK offline")):
        resp_sess_err = await async_client.post("/api/v1/documents/upload", files=files_valid, data=data_sess)
        assert resp_sess_err.status_code == 200

@pytest.mark.asyncio
async def test_get_and_list_documents(async_client):
    # 1. 404 on get_document
    assert (await async_client.get("/api/v1/documents/nonexistent")).status_code == 404

    # 2. 200 on get_document
    await db.save_document_metadata({
        "id": "doc-retrieval",
        "filename": "f.txt",
        "original_filename": "f.txt",
        "content_type": "text/plain",
        "size_bytes": 100,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "p",
        "uploaded_at": now_iso(),
        "user_id": "usr-retrieval",
        "custom_metadata": {}
    })
    get_res = await async_client.get("/api/v1/documents/doc-retrieval")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == "doc-retrieval"

    # 3. List documents with and without user_id
    list_with_u = await async_client.get("/api/v1/documents?user_id=usr-retrieval")
    assert list_with_u.status_code == 200
    assert len(list_with_u.json()) == 1

    list_default = await async_client.get("/api/v1/documents")
    assert list_default.status_code == 200

@pytest.mark.asyncio
async def test_analyze_document_endpoints(async_client):
    # 1. analyze_document_endpoint 404
    assert (await async_client.post("/api/v1/documents/missing/analyze")).status_code == 404

    # 2. analyze_document_endpoint 200
    await db.save_document_metadata({
        "id": "doc-to-analyze",
        "filename": "sow.txt",
        "original_filename": "sow.txt",
        "content_type": "text/plain",
        "size_bytes": 50,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "p",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "Master Services Agreement between Alpha and Beta."
    })
    an_res = await async_client.post("/api/v1/documents/doc-to-analyze/analyze")
    assert an_res.status_code == 200
    assert an_res.json()["document_id"] == "doc-to-analyze"
    assert "nature_of_document" in an_res.json()["analysis"]

    # 3. get_document_analysis 404
    assert (await async_client.get("/api/v1/documents/missing/analysis")).status_code == 404

    # 4. get_document_analysis with cached analysis
    get_an1 = await async_client.get("/api/v1/documents/doc-to-analyze/analysis")
    assert get_an1.status_code == 200
    assert "nature_of_document" in get_an1.json()["analysis"]

    # 5. get_document_analysis without cached analysis
    await db.save_document_metadata({
        "id": "doc-no-an",
        "filename": "note.txt",
        "original_filename": "note.txt",
        "content_type": "text/plain",
        "size_bytes": 30,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "p",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "Promissory note payable to Lender.",
        "custom_metadata": {}
    })
    get_an2 = await async_client.get("/api/v1/documents/doc-no-an/analysis")
    assert get_an2.status_code == 200
    assert get_an2.json()["analysis"]["nature_of_document"]["category"] == "Banking & Finance"

@pytest.mark.asyncio
async def test_document_routes_additional_branches(async_client, tmp_path):
    # 1. Upload document when session["state"] is not a dict (line 89)
    await db.save_session({"id": "s-non-dict-state", "user_id": "u", "document_ids": [], "state": "not_a_dict"})
    files = {"file": ("test.txt", b"Mutual NDA Agreement text.", "text/plain")}
    data = {"session_id": "s-non-dict-state"}
    up_res = await async_client.post("/api/v1/documents/upload", files=files, data=data)
    assert up_res.status_code == 200

    # 2. analyze_document_endpoint with empty extracted_text_snippet reading from gcs_path (lines 152-153)
    sample_file = tmp_path / "gcs_sample.txt"
    sample_file.write_text("Commercial Lease text read from local storage.", encoding="utf-8")
    await db.save_document_metadata({
        "id": "doc-read-gcs",
        "filename": "lease.txt",
        "original_filename": "lease.txt",
        "content_type": "text/plain",
        "size_bytes": 40,
        "gcs_uri": "file://" + str(sample_file),
        "gcs_bucket": "b",
        "gcs_path": str(sample_file),
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": None,
        "custom_metadata": {}
    })
    an_res = await async_client.post("/api/v1/documents/doc-read-gcs/analyze")
    assert an_res.status_code == 200
    assert "Real Estate" in an_res.json()["analysis"]["nature_of_document"]["category"]

    # 3. get_document_analysis with empty extracted_text_snippet reading from gcs_path (lines 189-190)
    await db.save_document_metadata({
        "id": "doc-read-gcs-2",
        "filename": "lease2.txt",
        "original_filename": "lease2.txt",
        "content_type": "text/plain",
        "size_bytes": 40,
        "gcs_uri": "file://" + str(sample_file),
        "gcs_bucket": "b",
        "gcs_path": str(sample_file),
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": None,
        "custom_metadata": {}
    })
    get_res = await async_client.get("/api/v1/documents/doc-read-gcs-2/analysis")
    assert get_res.status_code == 200
    assert "Real Estate" in get_res.json()["analysis"]["nature_of_document"]["category"]

    # 4. analyze_document_endpoint when text is empty (synthesizes snippet from analysis)
    await db.save_document_metadata({
        "id": "doc-empty-snippet",
        "filename": "scan.pdf",
        "original_filename": "scan.pdf",
        "content_type": "application/pdf",
        "size_bytes": 10,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "",
        "custom_metadata": {}
    })
    mock_an = {"legal_case": {"straightforward_summary": "Extracted verified contract terms."}}
    with patch("app.services.analysis_service.analysis_service.analyze_document", new_callable=AsyncMock, return_value=mock_an):
        empty_an_res = await async_client.post("/api/v1/documents/doc-empty-snippet/analyze")
        assert empty_an_res.status_code == 200
        updated_doc = await db.get_document_metadata("doc-empty-snippet")
        assert "Extracted verified contract terms." in updated_doc["extracted_text_snippet"]

