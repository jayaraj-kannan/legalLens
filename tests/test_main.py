import pytest
from app.main import app, lifespan, health_check
from app.config import settings

@pytest.mark.asyncio
async def test_health_check_endpoint(async_client):
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == settings.PROJECT_NAME
    assert data["version"] == settings.VERSION
    assert data["gcp_project"] == settings.GOOGLE_CLOUD_PROJECT
    assert data["gcs_bucket"] == settings.GCS_BUCKET_NAME

@pytest.mark.asyncio
async def test_direct_health_check_func():
    data = await health_check()
    assert data["status"] == "healthy"
    assert "version" in data

@pytest.mark.asyncio
async def test_lifespan_handler():
    # Directly invoke lifespan async context manager
    async with lifespan(app):
        pass
