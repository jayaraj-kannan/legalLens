import asyncio
import httpx

async def test_backend():
    print("Testing LegalLens Backend endpoints...")
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8080", timeout=10.0) as client:
        # 1. Health check
        resp = await client.get("/health")
        print("1. /health:", resp.status_code, resp.json())
        assert resp.status_code == 200

        # 2. Upload sample document
        sample_doc_content = b"""
        MUTUAL NON-DISCLOSURE AGREEMENT
        Parties: Alpha Corp and Beta Inc.
        Section 1. Confidential Information shall be kept strictly secret for a term of 5 years.
        Section 2. Governing law shall be the laws of the State of California.
        """
        files = {"file": ("sample_nda.txt", sample_doc_content, "text/plain")}
        data = {"user_id": "test_user_01", "description": "Sample NDA test"}
        upload_resp = await client.post("/api/v1/documents/upload", files=files, data=data)
        print("2. /api/v1/documents/upload:", upload_resp.status_code, upload_resp.json()["document"]["id"])
        doc_id = upload_resp.json()["document"]["id"]
        assert upload_resp.status_code == 200

        # 3. Create Session with document
        session_payload = {
            "user_id": "test_user_01",
            "title": "NDA Evaluation Session",
            "document_ids": [doc_id]
        }
        sess_resp = await client.post("/api/v1/sessions", json=session_payload)
        print("3. /api/v1/sessions create:", sess_resp.status_code, sess_resp.json()["id"])
        sess_id = sess_resp.json()["id"]
        assert sess_resp.status_code == 200

        # 4. List Sessions
        list_sess_resp = await client.get(f"/api/v1/sessions?user_id=test_user_01")
        print("4. /api/v1/sessions list count:", len(list_sess_resp.json()))
        assert len(list_sess_resp.json()) >= 1

        # 5. Check session audit events
        events_resp = await client.get(f"/api/v1/sessions/{sess_id}/events")
        print("5. /api/v1/sessions/{id}/events:", events_resp.status_code, events_resp.json())

        print("\nAll Backend service endpoints verified successfully!")

if __name__ == "__main__":
    asyncio.run(test_backend())
