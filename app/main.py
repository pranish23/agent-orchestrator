"""
FastAPI main application entry point
"""
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text, select
import redis.asyncio as redis
import structlog

from app.config import settings
from app.database import engine
from app.schemas import HealthResponse
from app.api import query_router, auth_router, sync_router, search_router, data_router

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
    
    # Initialize database and seed mock data
    try:
        from app.database import init_db, async_session_maker
        from app.services.search_service import SearchService
        from app.agents.gmail_agent import MOCK_EMAILS
        from app.agents.gcal_agent import MOCK_EVENTS
        from app.agents.drive_agent import MOCK_FILES
        from app.models import User
        from sqlalchemy import text
        
        await init_db()
        logger.info("Database initialized")
        
        async with async_session_maker() as db:
            user_id = "00000000-0000-0000-0000-000000000001"
            
            # Ensure mock user exists
            result = await db.execute(select(User).where(User.id == user_id))
            if not result.scalar():
                logger.info("Creating mock user for seeding")
                mock_user = User(id=user_id, email="user@example.com")
                db.add(mock_user)
                await db.commit()

            result = await db.execute(text("SELECT COUNT(*) FROM gmail_cache"))
            count = result.scalar()
            
            if count == 0:
                logger.info("Seeding database with mock data...")
                search_service = SearchService(db)
                
                for email in MOCK_EMAILS:
                    await search_service.index_email(
                        user_id=user_id, email_id=email["id"],
                        subject=email["subject"], sender=email["sender"],
                        body=email["body"], received_at=email["received_at"]
                    )
                for event in MOCK_EVENTS:
                    await search_service.index_event(
                        user_id=user_id, event_id=event["id"],
                        title=event["title"], description=event.get("description", ""),
                        attendees=event.get("attendees", []), start_time=event["start_time"]
                    )
                for file in MOCK_FILES:
                    await search_service.index_file(
                        user_id=user_id, file_id=file["id"],
                        name=file["name"], mime_type=file["mime_type"],
                        content_preview=file.get("content_preview", ""), modified_at=file["modified_at"]
                    )
                logger.info("Database seeding complete")
            else:
                logger.debug(f"Database already contains {count} records, skipping seed")
    except Exception as e:
        if "expected" in str(e) and "dimensions" in str(e):
            logger.warning("Embedding dimension mismatch detected. Dropping and recreating tables...")
            try:
                await init_db(drop_all=True)
                # Retry seeding after drop
                async with async_session_maker() as db:
                    user_id = "00000000-0000-0000-0000-000000000001"
                    # Re-create user
                    mock_user = User(id=user_id, email="user@example.com")
                    db.add(mock_user)
                    await db.commit()
                    
                    search_service = SearchService(db)
                    for email in MOCK_EMAILS:
                        await search_service.index_email(user_id=user_id, email_id=email["id"], subject=email["subject"], sender=email["sender"], body=email["body"], received_at=email["received_at"])
                    for event in MOCK_EVENTS:
                        await search_service.index_event(user_id=user_id, event_id=event["id"], title=event["title"], description=event.get("description", ""), attendees=event.get("attendees", []), start_time=event["start_time"])
                    for file in MOCK_FILES:
                        await search_service.index_file(user_id=user_id, file_id=file["id"], name=file["name"], mime_type=file["mime_type"], content_preview=file.get("content_preview", ""), modified_at=file["modified_at"])
                    logger.info("Database seeding complete after table recreation")
            except Exception as retry_e:
                logger.error(f"Re-seeding failed: {retry_e}")
        else:
            logger.error(f"Seeding failed: {str(e)}")
    
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
app.include_router(data_router, prefix="/api/v1", tags=["Data"])

