import json
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import aiosqlite
from google.cloud import firestore
from app.config import settings

logger = logging.getLogger(__name__)

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

class DatabaseProvider(ABC):
    @abstractmethod
    async def init_db(self):
        pass

    @abstractmethod
    async def save_document_metadata(self, doc_data: Dict[str, Any]):
        pass

    @abstractmethod
    async def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def save_session(self, session_data: Dict[str, Any]):
        pass

    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def list_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def update_session_state(self, session_id: str, state_delta: Dict[str, Any]):
        pass

    @abstractmethod
    async def log_session_event(self, session_id: str, event: Dict[str, Any]):
        pass

    @abstractmethod
    async def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        pass

# ==================== Google Cloud Firestore Provider ====================
class FirestoreDatabaseProvider(DatabaseProvider):
    def __init__(self):
        self.project = settings.GOOGLE_CLOUD_PROJECT
        self.client: Optional[firestore.Client] = None

    async def init_db(self):
        try:
            self.client = firestore.Client(project=self.project)
            logger.info(f"Initialized Cloud Firestore client for project: {self.project}")
        except Exception as e:
            logger.warning(f"Could not connect to Cloud Firestore: {e}")
            self.client = None

    async def save_document_metadata(self, doc_data: Dict[str, Any]):
        if not self.client:
            raise RuntimeError("Firestore is not connected")
        doc_id = doc_data["id"]
        self.client.collection("documents").document(doc_id).set(doc_data)

    async def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        doc = self.client.collection("documents").document(doc_id).get()
        return doc.to_dict() if doc.exists else None

    async def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        docs = self.client.collection("documents").where("user_id", "==", user_id).stream()
        return [d.to_dict() for d in docs]

    async def save_session(self, session_data: Dict[str, Any]):
        if not self.client:
            raise RuntimeError("Firestore is not connected")
        session_id = session_data["id"]
        self.client.collection("sessions").document(session_id).set(session_data, merge=True)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        if not self.client:
            return None
        doc = self.client.collection("sessions").document(session_id).get()
        return doc.to_dict() if doc.exists else None

    async def list_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        docs = self.client.collection("sessions").where("user_id", "==", user_id).stream()
        return [d.to_dict() for d in docs]

    async def update_session_state(self, session_id: str, state_delta: Dict[str, Any]):
        if not self.client:
            return
        doc_ref = self.client.collection("sessions").document(session_id)
        doc = doc_ref.get()
        if doc.exists:
            current_state = doc.to_dict().get("state", {})
            current_state.update(state_delta)
            doc_ref.update({
                "state": current_state,
                "updated_at": now_iso()
            })

    async def log_session_event(self, session_id: str, event: Dict[str, Any]):
        if not self.client:
            return
        self.client.collection("sessions").document(session_id).collection("events").add({
            **event,
            "recorded_at": now_iso()
        })

    async def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        if not self.client:
            return []
        events = self.client.collection("sessions").document(session_id).collection("events").order_by("recorded_at").stream()
        return [e.to_dict() for e in events]

    async def delete_session(self, session_id: str) -> bool:
        if not self.client:
            return False
        try:
            self.client.collection("sessions").document(session_id).delete()
            return True
        except Exception as e:
            logger.error(f"Error deleting session {session_id} from Firestore: {e}")
            return False


# ==================== Async SQLite Local Provider (Resilient Fallback) ====================
class SQLiteDatabaseProvider(DatabaseProvider):
    def __init__(self, db_path: str = "legallens.db"):
        self.db_path = db_path

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT,
                    original_filename TEXT,
                    content_type TEXT,
                    size_bytes INTEGER,
                    gcs_uri TEXT,
                    gcs_bucket TEXT,
                    gcs_path TEXT,
                    uploaded_at TEXT,
                    user_id TEXT,
                    extracted_text_snippet TEXT,
                    custom_metadata TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    app_name TEXT,
                    user_id TEXT,
                    title TEXT,
                    document_ids TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    state TEXT,
                    event_count INTEGER DEFAULT 0,
                    adk_synced INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS session_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    event_type TEXT,
                    payload TEXT,
                    recorded_at TEXT
                )
            """)
            await db.commit()
        logger.info(f"Initialized local SQLite Database at: {self.db_path}")

    async def save_document_metadata(self, doc_data: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO documents 
                (id, filename, original_filename, content_type, size_bytes, gcs_uri, gcs_bucket, gcs_path, uploaded_at, user_id, extracted_text_snippet, custom_metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                doc_data["id"],
                doc_data["filename"],
                doc_data["original_filename"],
                doc_data["content_type"],
                doc_data["size_bytes"],
                doc_data["gcs_uri"],
                doc_data["gcs_bucket"],
                doc_data["gcs_path"],
                doc_data["uploaded_at"],
                doc_data["user_id"],
                doc_data.get("extracted_text_snippet"),
                json.dumps(doc_data.get("custom_metadata", {}))
            ))
            await db.commit()

    async def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["custom_metadata"] = json.loads(res.get("custom_metadata") or "{}")
            return res

    async def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM documents WHERE user_id = ? ORDER BY uploaded_at DESC", (user_id,))
            rows = await cursor.fetchall()
            docs = []
            for r in rows:
                item = dict(r)
                item["custom_metadata"] = json.loads(item.get("custom_metadata") or "{}")
                docs.append(item)
            return docs

    async def save_session(self, session_data: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO sessions
                (id, app_name, user_id, title, document_ids, created_at, updated_at, state, event_count, adk_synced)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session_data["id"],
                session_data.get("app_name", settings.ADK_APP_NAME),
                session_data["user_id"],
                session_data.get("title", "Legal Consultation"),
                json.dumps(session_data.get("document_ids", [])),
                session_data.get("created_at", now_iso()),
                session_data.get("updated_at", now_iso()),
                json.dumps(session_data.get("state", {})),
                session_data.get("event_count", 0),
                1 if session_data.get("adk_synced", False) else 0
            ))
            await db.commit()

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            res["document_ids"] = json.loads(res.get("document_ids") or "[]")
            res["state"] = json.loads(res.get("state") or "{}")
            res["adk_synced"] = bool(res.get("adk_synced"))
            return res

    async def list_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM sessions WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
            rows = await cursor.fetchall()
            sessions = []
            for r in rows:
                item = dict(r)
                item["document_ids"] = json.loads(item.get("document_ids") or "[]")
                item["state"] = json.loads(item.get("state") or "{}")
                item["adk_synced"] = bool(item.get("adk_synced"))
                sessions.append(item)
            return sessions

    async def update_session_state(self, session_id: str, state_delta: Dict[str, Any]):
        curr = await self.get_session(session_id)
        if not curr:
            return
        curr_state = curr.get("state", {})
        curr_state.update(state_delta)
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions SET state = ?, updated_at = ? WHERE id = ?
            """, (json.dumps(curr_state), now_iso(), session_id))
            await db.commit()

    async def log_session_event(self, session_id: str, event: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO session_events (session_id, event_type, payload, recorded_at)
                VALUES (?, ?, ?, ?)
            """, (
                session_id,
                event.get("type", "unknown"),
                json.dumps(event),
                now_iso()
            ))
            await db.execute("UPDATE sessions SET event_count = event_count + 1 WHERE id = ?", (session_id,))
            await db.commit()

    async def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM session_events WHERE session_id = ? ORDER BY id ASC", (session_id,))
            rows = await cursor.fetchall()
            events = []
            for r in rows:
                events.append({
                    "id": r["id"],
                    "event_type": r["event_type"],
                    "recorded_at": r["recorded_at"],
                    **json.loads(r["payload"])
                })
            return events

    async def delete_session(self, session_id: str) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM session_events WHERE session_id = ?", (session_id,))
            cursor = await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()
            return cursor.rowcount > 0

# Hybrid Provider that uses Firestore if available, otherwise falls back smoothly to SQLite
class HybridDatabaseProvider(DatabaseProvider):
    def __init__(self):
        self.firestore = FirestoreDatabaseProvider()
        self.sqlite = SQLiteDatabaseProvider()
        self.active_provider: DatabaseProvider = self.sqlite

    async def init_db(self):
        await self.sqlite.init_db()
        self.active_provider = self.sqlite
        
        # Test Firestore connectivity
        if settings.DATABASE_TYPE == "firestore":
            try:
                await self.firestore.init_db()
                if self.firestore.client:
                    # Test probe write/read to verify API is enabled
                    test_doc = self.firestore.client.collection("_healthcheck").document("probe")
                    test_doc.set({"status": "ok", "ts": now_iso()})
                    self.active_provider = self.firestore
                    logger.info("Verified and using primary Google Cloud Firestore database.")
            except Exception as e:
                logger.warning(
                    f"Google Cloud Firestore is disabled or unreachable ({e}). "
                    "Seamlessly falling back to local persistent SQLite database provider."
                )
                self.active_provider = self.sqlite
        else:
            logger.info("Using local SQLite database provider as configured.")

    async def save_document_metadata(self, doc_data: Dict[str, Any]):
        return await self.active_provider.save_document_metadata(doc_data)

    async def get_document_metadata(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return await self.active_provider.get_document_metadata(doc_id)

    async def list_documents(self, user_id: str) -> List[Dict[str, Any]]:
        return await self.active_provider.list_documents(user_id)

    async def save_session(self, session_data: Dict[str, Any]):
        return await self.active_provider.save_session(session_data)

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return await self.active_provider.get_session(session_id)

    async def list_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        return await self.active_provider.list_sessions(user_id)

    async def update_session_state(self, session_id: str, state_delta: Dict[str, Any]):
        return await self.active_provider.update_session_state(session_id, state_delta)

    async def log_session_event(self, session_id: str, event: Dict[str, Any]):
        return await self.active_provider.log_session_event(session_id, event)

    async def get_session_events(self, session_id: str) -> List[Dict[str, Any]]:
        return await self.active_provider.get_session_events(session_id)

    async def delete_session(self, session_id: str) -> bool:
        return await self.active_provider.delete_session(session_id)

db = HybridDatabaseProvider()
