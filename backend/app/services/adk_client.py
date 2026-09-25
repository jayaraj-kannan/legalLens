import json
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class AdkClient:
    """
    Client interface that maps requests to the ADK FastAPI server based on resources/adk_server.json.
    - POST /apps/{app_name}/users/{user_id}/sessions
    - GET /apps/{app_name}/users/{user_id}/sessions/{session_id}
    - POST /run
    - POST /run_sse
    - GET /apps/{app_name}/users/{user_id}/sessions/{session_id}/artifacts
    """
    def __init__(self):
        self.base_url = settings.ADK_SERVER_URL.rstrip("/")
        self.app_name = settings.ADK_APP_NAME

    async def check_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def create_adk_session(
        self,
        user_id: str,
        session_id: Optional[str] = None,
        initial_state: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Calls POST /apps/{app_name}/users/{user_id}/sessions
        Payload schema: CreateSessionRequest (sessionId, state, events)
        """
        url = f"{self.base_url}/apps/{self.app_name}/users/{user_id}/sessions"
        payload = {}
        if session_id:
            payload["sessionId"] = session_id
        if initial_state:
            payload["state"] = initial_state

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def get_adk_session(self, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Calls GET /apps/{app_name}/users/{user_id}/sessions/{session_id}
        """
        url = f"{self.base_url}/apps/{self.app_name}/users/{user_id}/sessions/{session_id}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()

    async def delete_adk_session(self, user_id: str, session_id: str) -> bool:
        """
        Calls DELETE /apps/{app_name}/users/{user_id}/sessions/{session_id}
        """
        url = f"{self.base_url}/apps/{self.app_name}/users/{user_id}/sessions/{session_id}"
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.delete(url)
                return resp.status_code in (200, 204, 404)
        except Exception as e:
            logger.debug(f"Could not delete ADK session {session_id}: {e}")
            return False

    async def run_agent(
        self,
        user_id: str,
        session_id: str,
        prompt_text: str,
        streaming: bool = False,
        state_delta: Optional[Dict[str, Any]] = None,
        file_gcs_uris: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Calls POST /run
        Payload schema: RunAgentRequest (appName, userId, sessionId, newMessage, streaming, stateDelta)
        """
        url = f"{self.base_url}/run"
        parts = []

        # Add document references if provided
        if file_gcs_uris:
            for gcs_uri in file_gcs_uris:
                parts.append({
                    "fileData": {
                        "fileUri": gcs_uri,
                        "mimeType": "application/pdf"
                    }
                })

        # Add text prompt
        parts.append({"text": prompt_text})

        payload = {
            "appName": self.app_name,
            "userId": user_id,
            "sessionId": session_id,
            "streaming": streaming,
            "newMessage": {
                "role": "user",
                "parts": parts
            }
        }
        if state_delta:
            payload["stateDelta"] = state_delta

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code >= 400:
                logger.error(f"ADK Server returned status {resp.status_code}: {resp.text}")
            resp.raise_for_status()
            return resp.json()

    async def run_agent_stream(
        self,
        user_id: str,
        session_id: str,
        prompt_text: str,
        state_delta: Optional[Dict[str, Any]] = None,
        file_gcs_uris: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Calls POST /run_sse and streams Server-Sent Events back.
        """
        url = f"{self.base_url}/run_sse"
        parts = []
        if file_gcs_uris:
            for gcs_uri in file_gcs_uris:
                parts.append({
                    "fileData": {
                        "fileUri": gcs_uri,
                        "mimeType": "application/pdf"
                    }
                })
        parts.append({"text": prompt_text})

        payload = {
            "appName": self.app_name,
            "userId": user_id,
            "sessionId": session_id,
            "streaming": True,
            "newMessage": {
                "role": "user",
                "parts": parts
            }
        }
        if state_delta:
            payload["stateDelta"] = state_delta

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for chunk in response.aiter_text():
                    if chunk:
                        yield chunk

adk_client = AdkClient()
