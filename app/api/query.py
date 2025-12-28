"""
Query API endpoint for natural language processing
"""
from datetime import datetime
from uuid import uuid4
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.database import get_db
from app.schemas import QueryRequest, QueryResponse, IntentResult
from app.services.orchestrator import Orchestrator

router = APIRouter()
logger = structlog.get_logger()


@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Process a natural language query across Google Workspace services.
    
    This endpoint:
    1. Classifies the intent of the query
    2. Creates an execution plan
    3. Executes operations in parallel where possible
    4. Synthesizes a natural language response
    
    Examples:
    - "What's on my calendar next week?"
    - "Find emails from sarah@company.com about the budget"
    - "Cancel my Turkish Airlines flight"
    """
    start_time = time.time()
    
    try:
        # Create or get conversation ID
        conversation_id = request.conversation_id or uuid4()
        
        # Initialize orchestrator and process query
        orchestrator = Orchestrator(db)
        result = await orchestrator.process(
            query=request.query,
            conversation_id=conversation_id,
        )
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            "Query processed successfully",
            query=request.query,
            execution_time_ms=execution_time_ms,
            intent=result.get("intent", {}).get("intent"),
        )
        
        return QueryResponse(
            conversation_id=conversation_id,
            response=result["response"],
            intent=IntentResult(**result["intent"]) if result.get("intent") else None,
            actions_taken=result.get("actions_taken", []),
            execution_time_ms=execution_time_ms,
        )
        
    except Exception as e:
        logger.error("Query processing failed", error=str(e), query=request.query)
        raise HTTPException(status_code=500, detail=f"Failed to process query: {str(e)}")
