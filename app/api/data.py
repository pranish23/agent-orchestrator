"""
Data API endpoint for fetching cached data for the testing UI
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime
import structlog

from app.database import get_db
from app.models import GmailCache, GCalCache, GDriveCache

router = APIRouter()
logger = structlog.get_logger()


# ============ Response Schemas ============

class GmailDataItem(BaseModel):
    """Gmail cache item for display"""
    id: str
    email_id: str
    subject: Optional[str] = None
    sender: Optional[str] = None
    body_preview: Optional[str] = None
    received_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class GCalDataItem(BaseModel):
    """Calendar cache item for display"""
    id: str
    event_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    attendees: Optional[List[str]] = None
    
    class Config:
        from_attributes = True


class GDriveDataItem(BaseModel):
    """Drive cache item for display"""
    id: str
    file_id: str
    name: Optional[str] = None
    mime_type: Optional[str] = None
    content_preview: Optional[str] = None
    modified_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DataResponse(BaseModel):
    """Generic data response"""
    items: List[dict]
    count: int


# ============ Endpoints ============

@router.get("/data/gmail", response_model=DataResponse, tags=["Data"])
async def get_gmail_data(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get Gmail cache data for display.
    Returns only columns used for embeddings (excludes embedding vector).
    """
    try:
        result = await db.execute(
            select(
                GmailCache.id,
                GmailCache.email_id,
                GmailCache.subject,
                GmailCache.sender,
                GmailCache.body_preview,
                GmailCache.received_at
            ).order_by(GmailCache.received_at.desc()).limit(limit)
        )
        rows = result.fetchall()
        
        items = [
            {
                "id": str(row.id),
                "email_id": row.email_id,
                "subject": row.subject,
                "sender": row.sender,
                "body_preview": row.body_preview[:200] if row.body_preview else None,
                "received_at": row.received_at.isoformat() if row.received_at else None
            }
            for row in rows
        ]
        
        return DataResponse(items=items, count=len(items))
        
    except Exception as e:
        logger.error("Failed to fetch Gmail data", error=str(e))
        return DataResponse(items=[], count=0)


@router.get("/data/gcal", response_model=DataResponse, tags=["Data"])
async def get_gcal_data(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get Calendar cache data for display.
    Returns only columns used for embeddings (excludes embedding vector).
    """
    try:
        result = await db.execute(
            select(
                GCalCache.id,
                GCalCache.event_id,
                GCalCache.title,
                GCalCache.description,
                GCalCache.location,
                GCalCache.start_time,
                GCalCache.end_time,
                GCalCache.attendees
            ).order_by(GCalCache.start_time.desc()).limit(limit)
        )
        rows = result.fetchall()
        
        items = [
            {
                "id": str(row.id),
                "event_id": row.event_id,
                "title": row.title,
                "description": row.description[:200] if row.description else None,
                "location": row.location,
                "start_time": row.start_time.isoformat() if row.start_time else None,
                "end_time": row.end_time.isoformat() if row.end_time else None,
                "attendees": row.attendees or []
            }
            for row in rows
        ]
        
        return DataResponse(items=items, count=len(items))
        
    except Exception as e:
        logger.error("Failed to fetch Calendar data", error=str(e))
        return DataResponse(items=[], count=0)


@router.get("/data/gdrive", response_model=DataResponse, tags=["Data"])
async def get_gdrive_data(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    Get Drive cache data for display.
    Returns only columns used for embeddings (excludes embedding vector).
    """
    try:
        result = await db.execute(
            select(
                GDriveCache.id,
                GDriveCache.file_id,
                GDriveCache.name,
                GDriveCache.mime_type,
                GDriveCache.content_preview,
                GDriveCache.modified_at
            ).order_by(GDriveCache.modified_at.desc()).limit(limit)
        )
        rows = result.fetchall()
        
        items = [
            {
                "id": str(row.id),
                "file_id": row.file_id,
                "name": row.name,
                "mime_type": row.mime_type,
                "content_preview": row.content_preview[:200] if row.content_preview else None,
                "modified_at": row.modified_at.isoformat() if row.modified_at else None
            }
            for row in rows
        ]
        
        return DataResponse(items=items, count=len(items))
        
    except Exception as e:
        logger.error("Failed to fetch Drive data", error=str(e))
        return DataResponse(items=[], count=0)
