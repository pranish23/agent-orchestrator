"""
Background sync tasks for Gmail, Calendar, and Drive
"""
import asyncio
import structlog
from datetime import datetime
from sqlalchemy import select

from app.celery_app import celery_app
from app.database import async_session_maker
from app.services.search_service import SearchService
from app.agents.gmail_agent import MOCK_EMAILS
from app.agents.gcal_agent import MOCK_EVENTS
from app.agents.drive_agent import MOCK_FILES

logger = structlog.get_logger()

# Mock user for development
USER_ID = "00000000-0000-0000-0000-000000000001"


async def run_sync_gmail():
    """Sync Gmail emails and generate embeddings"""
    logger.info("Starting Gmail sync task")
    async with async_session_maker() as db:
        search_service = SearchService(db)
        for email in MOCK_EMAILS:
            await search_service.index_email(
                user_id=USER_ID,
                email_id=email["id"],
                subject=email["subject"],
                sender=email["sender"],
                body=email["body"],
                received_at=email["received_at"]
            )
    logger.info("Gmail sync completed", items_synced=len(MOCK_EMAILS))
    return len(MOCK_EMAILS)


async def run_sync_gcal():
    """Sync Google Calendar events and generate embeddings"""
    logger.info("Starting GCal sync task")
    async with async_session_maker() as db:
        search_service = SearchService(db)
        for event in MOCK_EVENTS:
            await search_service.index_event(
                user_id=USER_ID,
                event_id=event["id"],
                title=event["title"],
                description=event.get("description", ""),
                attendees=event.get("attendees", []),
                start_time=event["start_time"]
            )
    logger.info("GCal sync completed", items_synced=len(MOCK_EVENTS))
    return len(MOCK_EVENTS)


async def run_sync_gdrive():
    """Sync Google Drive files and generate embeddings"""
    logger.info("Starting GDrive sync task")
    async with async_session_maker() as db:
        search_service = SearchService(db)
        for file in MOCK_FILES:
            await search_service.index_file(
                user_id=USER_ID,
                file_id=file["id"],
                name=file["name"],
                mime_type=file["mime_type"],
                content_preview=file.get("content_preview", ""),
                modified_at=file["modified_at"]
            )
    logger.info("GDrive sync completed", items_synced=len(MOCK_FILES))
    return len(MOCK_FILES)


@celery_app.task(bind=True, name="app.tasks.sync_tasks.sync_gmail")
def sync_gmail(self):
    loop = asyncio.get_event_loop()
    count = loop.run_until_complete(run_sync_gmail())
    return {"status": "success", "items_synced": count}


@celery_app.task(bind=True, name="app.tasks.sync_tasks.sync_gcal")
def sync_gcal(self):
    loop = asyncio.get_event_loop()
    count = loop.run_until_complete(run_sync_gcal())
    return {"status": "success", "items_synced": count}


@celery_app.task(bind=True, name="app.tasks.sync_tasks.sync_gdrive")
def sync_gdrive(self):
    loop = asyncio.get_event_loop()
    count = loop.run_until_complete(run_sync_gdrive())
    return {"status": "success", "items_synced": count}


@celery_app.task(bind=True, name="app.tasks.sync_tasks.sync_all")
def sync_all(self):
    """Sync all services"""
    logger.info("Starting full sync")
    
    sync_gmail.delay()
    sync_gcal.delay()
    sync_gdrive.delay()
    
    return {"status": "triggered", "services": ["gmail", "gcal", "gdrive"]}
