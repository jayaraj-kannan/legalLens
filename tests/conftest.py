import os
import tempfile
import pytest
import pytest_asyncio
import httpx
from httpx import ASGITransport

# Set test environment variables before importing app modules
os.environ["DATABASE_TYPE"] = "sqlite"
os.environ["GOOGLE_CLOUD_PROJECT"] = "test-project-123"
os.environ["GOOGLE_CLOUD_LOCATION"] = "us-south1"
os.environ["GCS_BUCKET_NAME"] = "test-bucket"
os.environ["ADK_SERVER_URL"] = "http://127.0.0.1:8000"
os.environ["ADK_APP_NAME"] = "legallens"

from app.config import settings
from app.services.database_service import db, SQLiteDatabaseProvider
from app.main import app

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch, tmp_path):
    """Provides a fresh isolated SQLite database for every test."""
    test_db_path = str(tmp_path / "test_legallens.db")
    provider = SQLiteDatabaseProvider(db_path=test_db_path)
    monkeypatch.setattr(db, "sqlite", provider)
    monkeypatch.setattr(db, "active_provider", provider)
    monkeypatch.setattr(settings, "DATABASE_TYPE", "sqlite")
    
    # Run init
    import asyncio
    asyncio.run(provider.init_db())
    yield provider

@pytest_asyncio.fixture
async def async_client():
    """Asynchronous HTTP test client for FastAPI routes."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
