"""
Search API endpoint for direct hybrid search
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db
from app.services.search_service import SearchService, SearchHit

router = APIRouter()
logger = structlog.get_logger()

@router.get("/search")
async def search(
    q: str = Query(..., description="Search query"),
    service: Optional[str] = Query(None, description="Filter by service (gmail, gcal, gdrive)"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform direct hybrid search across Google Workspace services.
    
    This uses pgvector for semantic similarity and keyword matching.
    """
    search_service = SearchService(db)
    
    # Map service string to list if provided
    services = [service.lower()] if service else None
    
    # Mock user ID for now
    user_id = "00000000-0000-0000-0000-000000000001"
    
    results = await search_service.search(
        query=q,
        user_id=user_id,
        services=services,
        limit=limit
    )
    
    return [hit.to_dict() for hit in results]
