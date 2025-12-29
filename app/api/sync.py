"""
Sync API endpoints for manual sync triggers and status
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db
from app.schemas import SyncTriggerRequest, SyncStatusResponse, BaseResponse

router = APIRouter()
logger = structlog.get_logger()


from app.tasks.sync_tasks import sync_gmail, sync_gcal, sync_gdrive

@router.post("/trigger", response_model=BaseResponse)
async def trigger_sync(
    request: SyncTriggerRequest = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger manual sync for Gmail, Calendar, and/or Drive.
    
    If no services specified, syncs all services.
    """
    services = request.services if request and request.services else ["gmail", "gcal", "gdrive"]
    
    logger.info("Sync triggered", services=services)
    
    if "gmail" in services:
        sync_gmail.delay()
    if "gcal" in services:
        sync_gcal.delay()
    if "gdrive" in services:
        sync_gdrive.delay()
    
    return BaseResponse(
        success=True,
        message=f"Sync triggered for: {', '.join(services)}",
    )


@router.get("/status", response_model=SyncStatusResponse)
async def get_sync_status(db: AsyncSession = Depends(get_db)):
    """
    Get the last sync timestamps and status for each service.
    """
    # Mock sync status for development
    return SyncStatusResponse(
        gmail={
            "last_sync_at": "2024-01-15T10:30:00Z",
            "items_synced": 150,
            "status": "idle",
        },
        gcal={
            "last_sync_at": "2024-01-15T10:30:00Z",
            "items_synced": 45,
            "status": "idle",
        },
        gdrive={
            "last_sync_at": "2024-01-15T10:30:00Z",
            "items_synced": 78,
            "status": "idle",
        },
    )
