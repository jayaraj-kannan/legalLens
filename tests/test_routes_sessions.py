import pytest
from unittest.mock import AsyncMock, patch
from app.services.database_service import db, now_iso
from app.services.adk_client import adk_client

@pytest.mark.asyncio
async def test_create_session_endpoint(async_client):
    # 1. Successful creation with ADK sync success
    with patch.object(adk_client, "create_adk_session", new_callable=AsyncMock) as mock_adk:
        mock_adk.return_value = {"id": "sess-test-1"}
        resp = await async_client.post("/api/v1/sessions", json={
            "user_id": "usr-1",
            "title": "Employment Review",
            "initial_state": {"flag": True}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Employment Review"
        assert data["adk_synced"] is True

    # 2. Creation when ADK sync fails (exception caught, adk_synced=False)
    with patch.object(adk_client, "create_adk_session", side_effect=Exception("ADK down")):
        resp2 = await async_client.post("/api/v1/sessions", json={
            "title": "Offline Session"
        })
        assert resp2.status_code == 200
        assert resp2.json()["adk_synced"] is False

@pytest.mark.asyncio
async def test_get_session_endpoint_branches(async_client):
    # 1. 404 Not Found
    resp_404 = await async_client.get("/api/v1/sessions/nonexistent-id")
    assert resp_404.status_code == 404

    # Save a test session in DB
    sess_data = {
        "id": "sess-sync-test",
        "app_name": "legallens",
        "user_id": "legal_user_default",
        "title": "Sync Test",
        "document_ids": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "state": {"step": 1},
        "event_count": 0,
        "adk_synced": False
    }
    await db.save_session(sess_data)

    # 2. ADK server returns None -> re-seeds session
    with patch.object(adk_client, "get_adk_session", new_callable=AsyncMock, return_value=None), \
         patch.object(adk_client, "create_adk_session", new_callable=AsyncMock) as mock_create:
        resp = await async_client.get("/api/v1/sessions/sess-sync-test")
        assert resp.status_code == 200
        assert resp.json()["adk_synced"] is True
        mock_create.assert_called_once()

    # 3. ADK server returns updated state -> syncs back to DB
    with patch.object(adk_client, "get_adk_session", new_callable=AsyncMock, return_value={"state": {"step": 2}}):
        resp_upd = await async_client.get("/api/v1/sessions/sess-sync-test")
        assert resp_upd.status_code == 200
        assert resp_upd.json()["state"]["step"] == 2

    # 4. ADK server raises Exception -> adk_synced=False
    with patch.object(adk_client, "get_adk_session", side_effect=Exception("ADK timeout")):
        resp_err = await async_client.get("/api/v1/sessions/sess-sync-test")
        assert resp_err.status_code == 200
        assert resp_err.json()["adk_synced"] is False

@pytest.mark.asyncio
async def test_update_session_patch_and_put(async_client):
    sess_data = {
        "id": "sess-upd-test",
        "user_id": "usr-upd",
        "title": "Initial Title",
        "document_ids": ["d1"],
        "state": {"a": 1}
    }
    await db.save_session(sess_data)

    # 404 for missing
    assert (await async_client.patch("/api/v1/sessions/missing", json={"title": "T"})).status_code == 404

    # Update via PATCH with ADK sync success
    with patch.object(adk_client, "create_adk_session", new_callable=AsyncMock):
        resp = await async_client.patch("/api/v1/sessions/sess-upd-test", json={
            "title": "Renamed Title",
            "document_ids": ["d1", "d2"],
            "state": {"b": 2}
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Renamed Title"
        assert data["document_ids"] == ["d1", "d2"]
        assert data["state"] == {"a": 1, "b": 2}

    # Update via PUT with ADK sync exception
    with patch.object(adk_client, "create_adk_session", side_effect=Exception("Sync failed")):
        resp_put = await async_client.put("/api/v1/sessions/sess-upd-test", json={
            "title": "Put Renamed Title"
        })
        assert resp_put.status_code == 200
        assert resp_put.json()["title"] == "Put Renamed Title"

@pytest.mark.asyncio
async def test_list_and_events_and_delete_session(async_client):
    # List sessions with and without query param
    await db.save_session({"id": "s-list-1", "user_id": "user-list"})
    list_resp = await async_client.get("/api/v1/sessions?user_id=user-list")
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1

    list_default = await async_client.get("/api/v1/sessions")
    assert list_default.status_code == 200

    # Events endpoint
    await db.log_session_event("s-list-1", {"type": "test_audit"})
    events_resp = await async_client.get("/api/v1/sessions/s-list-1/events")
    assert events_resp.status_code == 200
    assert len(events_resp.json()["events"]) >= 1

    # Delete session (with ADK delete success and exception)
    with patch.object(adk_client, "delete_adk_session", new_callable=AsyncMock):
        del_resp = await async_client.delete("/api/v1/sessions/s-list-1?user_id=user-list")
        assert del_resp.status_code == 200
        assert del_resp.json()["deleted"] is True

    # Delete with ADK exception
    await db.save_session({"id": "s-del-err", "user_id": "u"})
    with patch.object(adk_client, "delete_adk_session", side_effect=Exception("Failed")):
        del_err = await async_client.delete("/api/v1/sessions/s-del-err")
        assert del_err.status_code == 200
        assert del_err.json()["deleted"] is True

@pytest.mark.asyncio
async def test_session_dashboard_endpoints(async_client):
    # 1. 404 session not found
    assert (await async_client.get("/api/v1/sessions/missing/dashboard")).status_code == 404

    # 2. Session without documents, but has analysis in state
    await db.save_session({
        "id": "sess-dash-1",
        "user_id": "u",
        "document_ids": [],
        "state": {"analysis": {"score": 90}}
    })
    dash_1 = (await async_client.get("/api/v1/sessions/sess-dash-1/dashboard")).json()
    assert dash_1["has_document"] is True
    assert dash_1["analysis"]["score"] == 90

    # 3. Session without documents and no analysis in state
    await db.save_session({
        "id": "sess-dash-empty",
        "user_id": "u",
        "document_ids": [],
        "state": {}
    })
    dash_empty = (await async_client.get("/api/v1/sessions/sess-dash-empty/dashboard")).json()
    assert dash_empty["has_document"] is False

    # 4. Session with document_id, but document not in DB
    await db.save_session({
        "id": "sess-dash-missdoc",
        "user_id": "u",
        "document_ids": ["doc-missing-id"],
        "state": {"analysis": {"fallback": True}}
    })
    dash_miss = (await async_client.get("/api/v1/sessions/sess-dash-missdoc/dashboard")).json()
    assert dash_miss["has_document"] is True
    assert dash_miss["analysis"]["fallback"] is True

    await db.save_session({
        "id": "sess-dash-missdoc2",
        "user_id": "u",
        "document_ids": ["doc-missing-id-2"],
        "state": {}
    })
    dash_miss2 = (await async_client.get("/api/v1/sessions/sess-dash-missdoc2/dashboard")).json()
    assert dash_miss2["has_document"] is False

    # 5. Session with document that has analysis in custom_metadata
    await db.save_document_metadata({
        "id": "doc-with-meta",
        "filename": "f.pdf",
        "original_filename": "f.pdf",
        "content_type": "text/plain",
        "size_bytes": 10,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "p",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "custom_metadata": {"analysis": {"meta_analysis": True}}
    })
    await db.save_session({
        "id": "sess-with-doc",
        "user_id": "u",
        "document_ids": ["doc-with-meta"]
    })
    dash_doc = (await async_client.get("/api/v1/sessions/sess-with-doc/dashboard")).json()
    assert dash_doc["has_document"] is True
    assert dash_doc["analysis"]["meta_analysis"] is True

    # 6. Session with document without analysis in metadata, but session state has analysis
    await db.save_document_metadata({
        "id": "doc-no-meta",
        "filename": "f.pdf",
        "original_filename": "f.pdf",
        "content_type": "text/plain",
        "size_bytes": 10,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "p",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "custom_metadata": {}
    })
    await db.save_session({
        "id": "sess-cached-state",
        "user_id": "u",
        "document_ids": ["doc-no-meta"],
        "state": {"analysis": {"cached_in_state": True}}
    })
    dash_cached = (await async_client.get("/api/v1/sessions/sess-cached-state/dashboard")).json()
    assert dash_cached["has_document"] is True
    assert dash_cached["analysis"]["cached_in_state"] is True

    # 7. Session with document without analysis anywhere -> runs analysis
    await db.save_document_metadata({
        "id": "doc-fresh",
        "filename": "fresh.pdf",
        "original_filename": "fresh.pdf",
        "content_type": "text/plain",
        "size_bytes": 10,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "p",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "Non-Disclosure Agreement between A and B.",
        "custom_metadata": {}
    })
    await db.save_session({
        "id": "sess-fresh",
        "user_id": "u",
        "document_ids": ["doc-fresh"],
        "state": {}
    })
    dash_fresh = (await async_client.get("/api/v1/sessions/sess-fresh/dashboard")).json()
    assert dash_fresh["has_document"] is True
    assert "nature_of_document" in dash_fresh["analysis"]

@pytest.mark.asyncio
async def test_analyze_session_and_save_dashboard_endpoints(async_client):
    # analyze_session: 404 session
    assert (await async_client.post("/api/v1/sessions/missing/analyze")).status_code == 404

    # analyze_session: 400 no docs
    await db.save_session({"id": "s-no-docs", "user_id": "u", "document_ids": []})
    assert (await async_client.post("/api/v1/sessions/s-no-docs/analyze")).status_code == 400

    # analyze_session: 404 document missing
    await db.save_session({"id": "s-bad-doc", "user_id": "u", "document_ids": ["bad-doc"]})
    assert (await async_client.post("/api/v1/sessions/s-bad-doc/analyze")).status_code == 404

    # analyze_session: success with ADK sync
    await db.save_document_metadata({
        "id": "d-good",
        "filename": "good.pdf",
        "original_filename": "good.pdf",
        "content_type": "text/plain",
        "size_bytes": 10,
        "gcs_uri": "g",
        "gcs_bucket": "b",
        "gcs_path": "p",
        "uploaded_at": now_iso(),
        "user_id": "u",
        "extracted_text_snippet": "Employment agreement terms."
    })
    await db.save_session({"id": "s-good", "user_id": "u", "document_ids": ["d-good"]})

    with patch.object(adk_client, "create_adk_session", new_callable=AsyncMock):
        an_resp = await async_client.post("/api/v1/sessions/s-good/analyze")
        assert an_resp.status_code == 200
        assert an_resp.json()["document_id"] == "d-good"

    # save_session_dashboard POST / PUT
    assert (await async_client.post("/api/v1/sessions/missing/dashboard", json={"k": "v"})).status_code == 404

    with patch.object(adk_client, "create_adk_session", new_callable=AsyncMock):
        save_resp = await async_client.post("/api/v1/sessions/s-good/dashboard", json={"analysis": {"score": 95}})
        assert save_resp.status_code == 200
        assert save_resp.json()["analysis"]["score"] == 95

    with patch.object(adk_client, "create_adk_session", side_effect=Exception("ADK down")):
        save_resp2 = await async_client.put("/api/v1/sessions/s-good/dashboard", json={"score": 80})
        assert save_resp2.status_code == 200
        assert save_resp2.json()["analysis"]["score"] == 80

@pytest.mark.asyncio
async def test_sessions_routes_additional_branches(async_client, tmp_path):
    sample_file = tmp_path / "sess_gcs_file.txt"
    sample_file.write_text("Mutual Non-Disclosure Agreement content from local storage.", encoding="utf-8")

    # 1. get_session_dashboard when text is empty, read from gcs_path, and state is not a dict (lines 219-220, 228)
    await db.save_document_metadata({
        "id": "doc-sess-gcs",
        "filename": "nda.txt",
        "original_filename": "nda.txt",
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
    await db.save_session({
        "id": "s-non-dict-dashboard",
        "user_id": "u",
        "document_ids": ["doc-sess-gcs"],
        "state": "string_state_not_dict"
    })
    dash_resp = await async_client.get("/api/v1/sessions/s-non-dict-dashboard/dashboard")
    assert dash_resp.status_code == 200
    assert dash_resp.json()["has_document"] is True

    # 2. analyze_session when text is empty, read from gcs_path, state not a dict, ADK sync raises exception (lines 265-266, 276, 290-291)
    await db.save_document_metadata({
        "id": "doc-sess-an-fresh",
        "filename": "nda_an.txt",
        "original_filename": "nda_an.txt",
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
    await db.save_session({
        "id": "s-non-dict-analyze",
        "user_id": "u",
        "document_ids": ["doc-sess-an-fresh"],
        "state": "string_state_not_dict"
    })
    with patch.object(adk_client, "create_adk_session", side_effect=Exception("ADK timeout")):
        an_resp = await async_client.post("/api/v1/sessions/s-non-dict-analyze/analyze")
        assert an_resp.status_code == 200
        assert an_resp.json()["document_id"] == "doc-sess-an-fresh"

    # 4. analyze_session when text is empty (synthesizes snippet from analysis)
    await db.save_document_metadata({
        "id": "doc-sess-empty-snip",
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
    await db.save_session({
        "id": "s-empty-snip",
        "user_id": "u",
        "document_ids": ["doc-sess-empty-snip"],
        "state": {}
    })
    mock_an = {"legal_case": {"straightforward_summary": "Extracted verified session contract terms."}}
    with patch("app.services.analysis_service.analysis_service.analyze_document", new_callable=AsyncMock, return_value=mock_an):
        empty_an_resp = await async_client.post("/api/v1/sessions/s-empty-snip/analyze")
        assert empty_an_resp.status_code == 200
        doc_after = await db.get_document_metadata("doc-sess-empty-snip")
        assert "Extracted verified session contract terms." in doc_after["extracted_text_snippet"]

    # 5. save_session_dashboard when state is not a dict (line 312)
    await db.save_session({
        "id": "s-non-dict-save",
        "user_id": "u",
        "state": "string_state_not_dict"
    })
    save_resp = await async_client.post("/api/v1/sessions/s-non-dict-save/dashboard", json={"score": 88})
    assert save_resp.status_code == 200
    assert save_resp.json()["analysis"]["score"] == 88

