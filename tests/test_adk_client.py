import pytest
import httpx
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.adk_client import AdkClient

@pytest.mark.asyncio
async def test_adk_client_init_and_health():
    client = AdkClient()
    assert client.app_name == "legallens"

    # 1. Health check returns True on 200
    mock_resp = MagicMock(status_code=200)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp):
        assert await client.check_health() is True

    # 2. Health check returns False on 500
    mock_resp_500 = MagicMock(status_code=500)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp_500):
        assert await client.check_health() is False

    # 3. Health check returns False on Exception
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=Exception("Network error")):
        assert await client.check_health() is False

@pytest.mark.asyncio
async def test_create_adk_session():
    client = AdkClient()

    # With session_id and initial_state
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = {"id": "sess-1", "state": {"key": "val"}}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        res = await client.create_adk_session("usr-1", "sess-1", {"key": "val"})
        assert res["id"] == "sess-1"
        called_payload = mock_post.call_args[1]["json"]
        assert called_payload["sessionId"] == "sess-1"
        assert called_payload["state"] == {"key": "val"}

    # Without session_id and without initial_state
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        await client.create_adk_session("usr-1")
        called_payload = mock_post.call_args[1]["json"]
        assert "sessionId" not in called_payload
        assert "state" not in called_payload

@pytest.mark.asyncio
async def test_get_and_delete_adk_session():
    client = AdkClient()

    # 1. get_adk_session 200 OK
    mock_resp_200 = MagicMock(status_code=200)
    mock_resp_200.json.return_value = {"id": "sess-1"}
    mock_resp_200.raise_for_status = MagicMock()
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp_200):
        res = await client.get_adk_session("u1", "sess-1")
        assert res == {"id": "sess-1"}

    # 2. get_adk_session 404 Not Found
    mock_resp_404 = MagicMock(status_code=404)
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_resp_404):
        assert await client.get_adk_session("u1", "sess-none") is None

    # 3. delete_adk_session 200 / 204
    mock_del_200 = MagicMock(status_code=200)
    with patch("httpx.AsyncClient.delete", new_callable=AsyncMock, return_value=mock_del_200):
        assert await client.delete_adk_session("u1", "sess-1") is True

    # 4. delete_adk_session Exception
    with patch("httpx.AsyncClient.delete", new_callable=AsyncMock, side_effect=Exception("Failed")):
        assert await client.delete_adk_session("u1", "sess-1") is False

@pytest.mark.asyncio
async def test_run_agent_and_stream():
    client = AdkClient()

    # 1. run_agent standard call
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = [{"author": "orchestrator_agent", "content": {"parts": [{"text": "Hello"}]}}]
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:
        res = await client.run_agent(
            user_id="u1",
            session_id="s1",
            prompt_text="Help me",
            streaming=False,
            state_delta={"delta": 1},
            file_gcs_uris=["gs://bucket/file.pdf"]
        )
        assert len(res) == 1
        called_json = mock_post.call_args[1]["json"]
        assert called_json["sessionId"] == "s1"
        assert called_json["stateDelta"] == {"delta": 1}
        assert called_json["newMessage"]["parts"][0]["fileData"]["fileUri"] == "gs://bucket/file.pdf"
        assert called_json["newMessage"]["parts"][1]["text"] == "Help me"

    # 2. run_agent with status >= 400
    mock_resp_err = MagicMock(status_code=500, text="Internal ADK error")
    mock_resp_err.raise_for_status = MagicMock(side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=mock_resp_err))
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp_err):
        with pytest.raises(httpx.HTTPStatusError):
            await client.run_agent("u1", "s1", "Prompt")

    # 3. run_agent_stream
    class MockStreamResponse:
        def raise_for_status(self):
            pass
        async def aiter_text(self):
            yield "data: chunk 1\n\n"
            yield ""
            yield "data: chunk 2\n\n"

    class MockStreamContext:
        async def __aenter__(self):
            return MockStreamResponse()
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("httpx.AsyncClient.stream", return_value=MockStreamContext()):
        chunks = []
        async for chunk in client.run_agent_stream(
            user_id="u1",
            session_id="s1",
            prompt_text="Stream prompt",
            state_delta={"flag": True},
            file_gcs_uris=["gs://bucket/doc.pdf"]
        ):
            chunks.append(chunk)
        assert len(chunks) == 2
        assert "chunk 1" in chunks[0]
        assert "chunk 2" in chunks[1]
