import os
import pytest
from app.config import Settings

def test_settings_defaults():
    s = Settings()
    assert s.PROJECT_NAME == "LegalLens Backend API"
    assert s.VERSION == "1.0.0"
    assert s.API_V1_PREFIX == "/api/v1"
    assert s.DEFAULT_USER_ID == "legal_user_default"
    assert s.ADK_APP_NAME == "legallens"

def test_settings_env_overrides(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "custom-proj-999")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "europe-west1")
    monkeypatch.setenv("GCS_BUCKET_NAME", "my-custom-bucket")
    monkeypatch.setenv("DATABASE_TYPE", "sqlite")
    monkeypatch.setenv("ADK_SERVER_URL", "http://adk.internal:9000")
    
    s = Settings()
    assert s.GOOGLE_CLOUD_PROJECT == "custom-proj-999"
    assert s.GOOGLE_CLOUD_LOCATION == "europe-west1"
    assert s.GCS_BUCKET_NAME == "my-custom-bucket"
    assert s.DATABASE_TYPE == "sqlite"
    assert s.ADK_SERVER_URL == "http://adk.internal:9000"
