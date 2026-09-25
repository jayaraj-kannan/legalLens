from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "LegalLens Backend API"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # GCP configuration
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "legallens-509417")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-south1")
    GCS_BUCKET_NAME: str = os.getenv("GCS_BUCKET_NAME", "legallens-documents-509417")
    
    # Database mode: 'firestore' or 'sqlite'
    DATABASE_TYPE: str = os.getenv("DATABASE_TYPE", "firestore")
    SQLITE_DB_URL: str = os.getenv("SQLITE_DB_URL", "sqlite+aiosqlite:///./legallens.db")
    
    # ADK API Server configuration
    ADK_SERVER_URL: str = os.getenv("ADK_SERVER_URL", "http://127.0.0.1:8000")
    ADK_APP_NAME: str = os.getenv("ADK_APP_NAME", "legallens")
    DEFAULT_USER_ID: str = "legal_user_default"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
