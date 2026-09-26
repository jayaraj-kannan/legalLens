import pytest
import os
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.database_service import (
    now_iso,
    DatabaseProvider,
    FirestoreDatabaseProvider,
    SQLiteDatabaseProvider,
    HybridDatabaseProvider
)
from app.config import settings

def test_now_iso():
    iso = now_iso()
    assert isinstance(iso, str)
    assert "T" in iso

@pytest.mark.asyncio
async def test_sqlite_provider_complete_lifecycle(tmp_path):
    db_file = str(tmp_path / "sqlite_test.db")
    provider = SQLiteDatabaseProvider(db_path=db_file)
    await provider.init_db()

    # 1. Document Metadata CRUD
    doc_payload = {
        "id": "doc-001",
        "filename": "lease.pdf",
        "original_filename": "lease_v1.pdf",
        "content_type": "application/pdf",
        "size_bytes": 5000,
        "gcs_uri": "gs://bucket/lease.pdf",
        "gcs_bucket": "bucket",
        "gcs_path": "uploads/lease.pdf",
        "uploaded_at": now_iso(),
        "user_id": "user-test",
        "extracted_text_snippet": "Commercial Lease Agreement",
        "custom_metadata": {"rent": 2500}
    }
    await provider.save_document_metadata(doc_payload)

    # Fetch document
    fetched = await provider.get_document_metadata("doc-001")
    assert fetched is not None
    assert fetched["id"] == "doc-001"
    assert fetched["custom_metadata"]["rent"] == 2500

    # Fetch missing document
    missing = await provider.get_document_metadata("doc-nonexistent")
    assert missing is None

    # List documents
    docs = await provider.list_documents("user-test")
    assert len(docs) == 1
    assert docs[0]["id"] == "doc-001"
    assert docs[0]["custom_metadata"]["rent"] == 2500

    docs_empty = await provider.list_documents("user-unknown")
    assert len(docs_empty) == 0

    # 2. Session CRUD
    sess_payload = {
        "id": "sess-001",
        "app_name": "legallens",
        "user_id": "user-test",
        "title": "Lease Review",
        "document_ids": ["doc-001"],
        "state": {"stage": "initial"},
        "event_count": 0,
        "adk_synced": True
    }
    await provider.save_session(sess_payload)

    # Get session
    sess = await provider.get_session("sess-001")
    assert sess is not None
    assert sess["id"] == "sess-001"
    assert sess["title"] == "Lease Review"
    assert sess["document_ids"] == ["doc-001"]
    assert sess["state"]["stage"] == "initial"
    assert sess["adk_synced"] is True

    # Get missing session
    missing_sess = await provider.get_session("sess-nonexistent")
    assert missing_sess is None

    # List sessions
    sessions = await provider.list_sessions("user-test")
    assert len(sessions) == 1
    assert sessions[0]["id"] == "sess-001"

    # Update session state for existing session
    await provider.update_session_state("sess-001", {"stage": "analyzed", "risk": "low"})
    updated_sess = await provider.get_session("sess-001")
    assert updated_sess["state"]["stage"] == "analyzed"
    assert updated_sess["state"]["risk"] == "low"

    # Update session state for non-existent session
    await provider.update_session_state("sess-none", {"stage": "error"})

    # Update session title
    renamed = await provider.update_session_title("sess-001", "Updated Lease Title")
    assert renamed is not None
    assert renamed["title"] == "Updated Lease Title"

    # 3. Session Events
    await provider.log_session_event("sess-001", {"type": "query", "text": "What is the rent?"})
    events = await provider.get_session_events("sess-001")
    assert len(events) == 1
    assert events[0]["type"] == "query"
    assert events[0]["text"] == "What is the rent?"

    # Check that event count incremented in session
    sess_with_events = await provider.get_session("sess-001")
    assert sess_with_events["event_count"] == 1

    # 4. Delete Session
    del_success = await provider.delete_session("sess-001")
    assert del_success is True
    assert await provider.get_session("sess-001") is None
    assert len(await provider.get_session_events("sess-001")) == 0

    del_fail = await provider.delete_session("sess-nonexistent")
    assert del_fail is False

@pytest.mark.asyncio
async def test_firestore_provider_branches():
    provider = FirestoreDatabaseProvider()

    # 1. When client is None
    provider.client = None
    with pytest.raises(RuntimeError):
        await provider.save_document_metadata({"id": "d1"})
    assert await provider.get_document_metadata("d1") is None
    assert await provider.list_documents("u1") == []
    with pytest.raises(RuntimeError):
        await provider.save_session({"id": "s1"})
    assert await provider.get_session("s1") is None
    assert await provider.list_sessions("u1") == []
    await provider.update_session_state("s1", {"k": "v"})
    assert await provider.update_session_title("s1", "new") is None
    await provider.log_session_event("s1", {"e": 1})
    assert await provider.get_session_events("s1") == []
    assert await provider.delete_session("s1") is False

    # 2. init_db with exception
    with patch("google.cloud.firestore.Client", side_effect=Exception("Connection refused")):
        await provider.init_db()
        assert provider.client is None

    # 3. init_db with mock client
    mock_client = MagicMock()
    with patch("google.cloud.firestore.Client", return_value=mock_client):
        await provider.init_db()
        assert provider.client is mock_client

    # 4. save_document_metadata with client
    mock_coll = MagicMock()
    mock_doc = MagicMock()
    mock_client.collection.return_value = mock_coll
    mock_coll.document.return_value = mock_doc

    await provider.save_document_metadata({"id": "doc-fs-1", "user_id": "u1"})
    mock_doc.set.assert_called_once_with({"id": "doc-fs-1", "user_id": "u1"})

    # 5. get_document_metadata (exists vs not exists)
    mock_snapshot = MagicMock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {"id": "doc-fs-1"}
    mock_doc.get.return_value = mock_snapshot
    res = await provider.get_document_metadata("doc-fs-1")
    assert res == {"id": "doc-fs-1"}

    mock_snapshot.exists = False
    res_none = await provider.get_document_metadata("doc-fs-missing")
    assert res_none is None

    # 6. list_documents with client
    doc_snap1 = MagicMock()
    doc_snap1.to_dict.return_value = {"id": "doc-1"}
    mock_coll.where.return_value.stream.return_value = [doc_snap1]
    res_list = await provider.list_documents("u1")
    assert res_list == [{"id": "doc-1"}]

    # 7. save_session with client
    await provider.save_session({"id": "sess-fs-1"})
    mock_doc.set.assert_called_with({"id": "sess-fs-1"}, merge=True)

    # 8. get_session (exists vs not exists)
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {"id": "sess-fs-1"}
    s_res = await provider.get_session("sess-fs-1")
    assert s_res == {"id": "sess-fs-1"}

    mock_snapshot.exists = False
    assert await provider.get_session("sess-none") is None

    # 9. list_sessions with client
    sess_snap1 = MagicMock()
    sess_snap1.to_dict.return_value = {"id": "sess-1"}
    mock_coll.where.return_value.stream.return_value = [sess_snap1]
    assert await provider.list_sessions("u1") == [{"id": "sess-1"}]

    # 10. update_session_state
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {"state": {"step": 1}}
    await provider.update_session_state("sess-fs-1", {"step": 2})
    mock_doc.update.assert_called()

    # When state is not a dict in Firestore (line 122)
    mock_snapshot.to_dict.return_value = {"state": "not_a_dict"}
    await provider.update_session_state("sess-fs-1", {"step": 3})

    # 11. update_session_title (success & exception)
    mock_doc.update.reset_mock()
    mock_snapshot.exists = True
    mock_snapshot.to_dict.return_value = {"id": "sess-fs-1", "title": "New Title"}
    title_res = await provider.update_session_title("sess-fs-1", "New Title")
    assert title_res == {"id": "sess-fs-1", "title": "New Title"}

    mock_doc.update.side_effect = Exception("Write error")
    err_title = await provider.update_session_title("sess-fs-1", "Fail Title")
    assert err_title is None
    mock_doc.update.side_effect = None

    # 12. log_session_event and get_session_events
    mock_subcoll = MagicMock()
    mock_doc.collection.return_value = mock_subcoll
    await provider.log_session_event("sess-fs-1", {"type": "test_event"})
    mock_subcoll.add.assert_called()

    event_snap = MagicMock()
    event_snap.to_dict.return_value = {"type": "test_event"}
    mock_subcoll.order_by.return_value.stream.return_value = [event_snap]
    events_res = await provider.get_session_events("sess-fs-1")
    assert events_res == [{"type": "test_event"}]

    # 13. delete_session (success and exception)
    del_res = await provider.delete_session("sess-fs-1")
    assert del_res is True

    mock_doc.delete.side_effect = Exception("Delete error")
    del_fail = await provider.delete_session("sess-fs-1")
    assert del_fail is False

@pytest.mark.asyncio
async def test_hybrid_provider_delegations(tmp_path):
    hybrid = HybridDatabaseProvider()
    test_db = str(tmp_path / "hybrid_test.db")
    hybrid.sqlite = SQLiteDatabaseProvider(db_path=test_db)
    
    # Init with SQLite mode
    with patch.object(settings, "DATABASE_TYPE", "sqlite"):
        await hybrid.init_db()
        assert hybrid.active_provider == hybrid.sqlite

    # Test all delegations
    await hybrid.save_document_metadata({"id": "h-doc", "filename": "f", "original_filename": "f", "content_type": "t", "size_bytes": 1, "gcs_uri": "g", "gcs_bucket": "b", "gcs_path": "p", "uploaded_at": now_iso(), "user_id": "u", "custom_metadata": {}})
    assert (await hybrid.get_document_metadata("h-doc"))["id"] == "h-doc"
    assert len(await hybrid.list_documents("u")) == 1

    await hybrid.save_session({"id": "h-sess", "user_id": "u", "title": "T"})
    assert (await hybrid.get_session("h-sess"))["id"] == "h-sess"
    assert len(await hybrid.list_sessions("u")) == 1

    await hybrid.update_session_state("h-sess", {"k": "v"})
    await hybrid.update_session_title("h-sess", "T2")
    await hybrid.log_session_event("h-sess", {"type": "e"})
    assert len(await hybrid.get_session_events("h-sess")) == 1
    assert await hybrid.delete_session("h-sess") is True

    # Test Firestore mode success
    mock_fs_client = MagicMock()
    hybrid_fs = HybridDatabaseProvider()
    hybrid_fs.sqlite = SQLiteDatabaseProvider(db_path=str(tmp_path / "hybrid_fs.db"))
    hybrid_fs.firestore.client = mock_fs_client
    with patch.object(settings, "DATABASE_TYPE", "firestore"), \
         patch.object(hybrid_fs.firestore, "init_db", AsyncMock()), \
         patch.object(mock_fs_client, "collection") as mock_col:
        mock_col.return_value.document.return_value.set = MagicMock()
        await hybrid_fs.init_db()
        assert hybrid_fs.active_provider == hybrid_fs.firestore

    # Test Firestore mode fallback on error
    hybrid_fs_err = HybridDatabaseProvider()
    hybrid_fs_err.sqlite = SQLiteDatabaseProvider(db_path=str(tmp_path / "hybrid_err.db"))
    with patch.object(settings, "DATABASE_TYPE", "firestore"), \
         patch.object(hybrid_fs_err.firestore, "init_db", AsyncMock(side_effect=Exception("Firestore offline"))):
        await hybrid_fs_err.init_db()
        assert hybrid_fs_err.active_provider == hybrid_fs_err.sqlite
