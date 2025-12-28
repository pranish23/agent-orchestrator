"""
Pydantic schemas for API request/response validation
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr


# ============ Base Schemas ============

class BaseResponse(BaseModel):
    """Base response with common fields"""
    success: bool = True
    message: Optional[str] = None


# ============ Query Schemas ============

class QueryRequest(BaseModel):
    """Request schema for natural language queries"""
    query: str = Field(..., min_length=1, max_length=1000, description="Natural language query")
    conversation_id: Optional[UUID] = Field(None, description="Continue existing conversation")


class IntentResult(BaseModel):
    """Parsed intent from query"""
    services: List[str] = Field(default_factory=list, description="Services to query: gmail, gcal, drive")
    intent: str = Field(..., description="Classified intent type")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    steps: List[str] = Field(default_factory=list, description="Execution steps")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Classification confidence")


class ActionTaken(BaseModel):
    """An action taken during query execution"""
    service: str
    operation: str
    status: str  # success, failed, skipped
    details: Optional[str] = None


class QueryResponse(BaseModel):
    """Response schema for queries"""
    conversation_id: UUID
    response: str = Field(..., description="Natural language response")
    intent: Optional[IntentResult] = None
    actions_taken: List[ActionTaken] = Field(default_factory=list)
    execution_time_ms: int = Field(0, description="Total execution time in milliseconds")


# ============ Gmail Schemas ============

class EmailResult(BaseModel):
    """Email search result"""
    email_id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    recipients: Optional[List[str]] = None
    body_preview: Optional[str] = None
    received_at: Optional[datetime] = None
    relevance_score: float = 0.0


class DraftEmailRequest(BaseModel):
    """Request to draft an email"""
    to: List[EmailStr]
    subject: str
    body: str
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None


# ============ Calendar Schemas ============

class EventResult(BaseModel):
    """Calendar event result"""
    event_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attendees: Optional[List[str]] = None
    relevance_score: float = 0.0


class CreateEventRequest(BaseModel):
    """Request to create a calendar event"""
    title: str
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    location: Optional[str] = None
    attendees: Optional[List[EmailStr]] = None


# ============ Drive Schemas ============

class FileResult(BaseModel):
    """Drive file result"""
    file_id: str
    name: Optional[str] = None
    mime_type: Optional[str] = None
    content_preview: Optional[str] = None
    modified_at: Optional[datetime] = None
    relevance_score: float = 0.0


# ============ Sync Schemas ============

class SyncTriggerRequest(BaseModel):
    """Request to trigger manual sync"""
    services: Optional[List[str]] = Field(None, description="Services to sync, default all")


class SyncStatusResponse(BaseModel):
    """Sync status for all services"""
    gmail: Optional[Dict[str, Any]] = None
    gcal: Optional[Dict[str, Any]] = None
    gdrive: Optional[Dict[str, Any]] = None


# ============ Health Schemas ============

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = "healthy"
    version: str = "1.0.0"
    database: str = "connected"
    redis: str = "connected"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
