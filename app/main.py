"""
FastAPI main application entry point
"""
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
import redis.asyncio as redis
import structlog

from app.config import settings
from app.database import engine
from app.schemas import HealthResponse
from app.api import query_router, auth_router, sync_router, search_router

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Redis client (initialized on startup)
redis_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global redis_client
    
    # Startup
    logger.info("Starting Agentic Google Workspace Orchestrator")
    
    # Initialize Redis
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    app.state.redis = redis_client
    
    logger.info("Connected to Redis", url=settings.redis_url)
    
    yield
    
    # Shutdown
    logger.info("Shutting down orchestrator")
    if redis_client:
        await redis_client.close()
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title="Agentic Google Workspace Orchestrator",
    description="Intelligent orchestrator for Gmail, Calendar, and Drive using natural language",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Health Endpoints ============

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    db_status = "connected"
    redis_status = "connected"
    
    # Check database connection
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check Redis connection
    try:
        if app.state.redis:
            await app.state.redis.ping()
    except Exception as e:
        redis_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy" if db_status == "connected" and redis_status == "connected" else "degraded",
        database=db_status,
        redis=redis_status,
        timestamp=datetime.utcnow(),
    )


@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "name": "Agentic Google Workspace Orchestrator",
        "version": "1.0.0",
        "docs": "/docs",
    }


# ============ Include Routers ============

app.include_router(query_router, prefix="/api/v1", tags=["Query"])
app.include_router(search_router, prefix="/api/v1", tags=["Search"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(sync_router, prefix="/api/v1/sync", tags=["Sync"])
