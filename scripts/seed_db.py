"""
Seeding script to populate the database with mock data for testing and demo.
"""
import asyncio
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.database import engine, async_session_maker
from app.models import User, GmailCache, GCalCache, GDriveCache
from app.agents.gmail_agent import GmailAgent
from app.agents.gcal_agent import GCalAgent
from app.agents.drive_agent import DriveAgent
from app.services.search_service import SearchService

MOCK_USER_ID = "00000000-0000-0000-0000-000000000001"

async def seed_data():
    """Seed the database with mock data"""
    print("Starting database seeding...")
    
    async with async_session_maker() as session:
        # 1. Create Mock User
        try:
            user = User(
                id=UUID(MOCK_USER_ID),
                email="user@example.com",
            )
            session.add(user)
            await session.commit()
            print(f"Created mock user: {MOCK_USER_ID}")
        except Exception as e:
            await session.rollback()
            print(f"Mock user already exists or error: {str(e)}")
        
        # 2. Sync data from mock agents to DB
        search_service = SearchService(session)
        
        # Gmail
        gmail_agent = GmailAgent(MOCK_USER_ID)
        emails = await gmail_agent.search("")
        print(f"Indexing {len(emails)} emails...")
        for email in emails:
            # Get full context
            context = await gmail_agent.get_context(email.id)
            await search_service.index_email(
                user_id=MOCK_USER_ID,
                email_id=email.id,
                subject=email.title,
                sender=email.metadata.get("sender", "unknown@example.com"),
                body=context.get("body", ""),
                received_at=datetime.fromisoformat(context["received_at"])
            )
            
        # GCal
        gcal_agent = GCalAgent(MOCK_USER_ID)
        events = await gcal_agent.search("")
        print(f"Indexing {len(events)} events...")
        for event in events:
            # Get full context to get attendees
            context = await gcal_agent.get_context(event.id)
            await search_service.index_event(
                user_id=MOCK_USER_ID,
                event_id=event.id,
                title=event.title,
                description=context.get("description", ""),
                attendees=context.get("attendees", []),
                start_time=datetime.fromisoformat(context["start_time"])
            )
            
        # GDrive
        gdrive_agent = DriveAgent(MOCK_USER_ID)
        files = await gdrive_agent.search("")
        print(f"Indexing {len(files)} files...")
        for file in files:
            context = await gdrive_agent.get_context(file.id)
            await search_service.index_file(
                user_id=MOCK_USER_ID,
                file_id=file.id,
                name=file.title,
                mime_type=file.metadata.get("mime_type", "application/octet-stream"),
                content_preview=context.get("content_preview", file.preview),
                modified_at=datetime.fromisoformat(context["modified_at"])
            )
            
    print("Database seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_data())
