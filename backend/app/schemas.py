from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime

# Document models
class DocumentMetadata(BaseModel):
    id: str
    filename: str
    original_filename: str
    content_type: str
    size_bytes: int
    gcs_uri: str
    gcs_bucket: str
    gcs_path: str
    uploaded_at: str
    user_id: str
    extracted_text_snippet: Optional[str] = None
    custom_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class DocumentUploadResponse(BaseModel):
    document: DocumentMetadata
    message: str = "Document successfully uploaded to Google Cloud Storage"

# Session models
class SessionCreateRequest(BaseModel):
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    title: Optional[str] = "Legal Consultation"
    document_ids: Optional[List[str]] = Field(default_factory=list)
    initial_state: Optional[Dict[str, Any]] = Field(default_factory=dict)

class SessionRecord(BaseModel):
    id: str
    app_name: str
    user_id: str
    title: str = "Legal Consultation"
    document_ids: List[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
    state: Dict[str, Any] = Field(default_factory=dict)
    event_count: int = 0
    adk_synced: bool = False

# Query & Chat Models
class QueryAgentRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    prompt: str
    document_ids: Optional[List[str]] = Field(default_factory=list)
    streaming: bool = False
    state_delta: Optional[Dict[str, Any]] = None

class AgentResponse(BaseModel):
    session_id: str
    user_id: str
    response_text: str
    agent_name: Optional[str] = None
    citations: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    raw_events: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
