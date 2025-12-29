"""
Tests for Agent classes
"""
import pytest
from datetime import datetime, timedelta
from app.agents.gmail_agent import GmailAgent
from app.agents.gcal_agent import GCalAgent
from app.agents.drive_agent import DriveAgent


class TestGmailAgent:
    """Test suite for Gmail Agent"""
    
    @pytest.fixture
    def agent(self):
        return GmailAgent("test-user-001")
    
    @pytest.mark.asyncio
    async def test_search_by_keyword(self, agent):
        """Test keyword search"""
        results = await agent.search("Turkish Airlines")
        
        assert len(results) > 0
        assert any("Turkish" in r.title for r in results)
    
    @pytest.mark.asyncio
    async def test_search_by_sender(self, agent):
        """Test search by sender filter"""
        results = await agent.search_by_sender("sarah@company.com")
        
        assert len(results) > 0
        assert all("sarah" in r.metadata["sender"].lower() for r in results)
    
    @pytest.mark.asyncio
    async def test_draft_email(self, agent):
        """Test drafting an email"""
        result = await agent.execute("draft_email", {
            "to": ["test@example.com"],
            "subject": "Test Subject",
            "body": "Test body content",
        })
        
        assert result.success
        assert result.data["draft_id"]
    
    @pytest.mark.asyncio
    async def test_get_context(self, agent):
        """Test getting full email context"""
        context = await agent.get_context("email-001")
        
        assert context is not None
        assert "Turkish Airlines" in context["subject"]


class TestGCalAgent:
    """Test suite for Google Calendar Agent"""
    
    @pytest.fixture
    def agent(self):
        return GCalAgent("test-user-001")
    
    @pytest.mark.asyncio
    async def test_search_events(self, agent):
        """Test event search"""
        results = await agent.search("meeting")
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_search_by_attendee(self, agent):
        """Test search by attendee filter"""
        results = await agent.get_events_by_attendee("sarah@company.com")
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_get_events_next_week(self, agent):
        """Test getting next week's events"""
        results = await agent.get_events_next_week()
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_create_event(self, agent):
        """Test creating an event"""
        result = await agent.execute("create_event", {
            "title": "Test Meeting",
            "start_time": datetime.now() + timedelta(days=1),
            "end_time": datetime.now() + timedelta(days=1, hours=1),
        })
        
        assert result.success
        assert result.data["event_id"]
    
    @pytest.mark.asyncio
    async def test_delete_event(self, agent):
        """Test deleting an event"""
        # First create
        create_result = await agent.execute("create_event", {
            "title": "To Delete",
            "start_time": datetime.now(),
            "end_time": datetime.now() + timedelta(hours=1),
        })
        
        # Then delete
        delete_result = await agent.execute("delete_event", {
            "event_id": create_result.data["event_id"]
        })
        
        assert delete_result.success


class TestDriveAgent:
    """Test suite for Google Drive Agent"""
    
    @pytest.fixture
    def agent(self):
        return DriveAgent("test-user-001")
    
    @pytest.mark.asyncio
    async def test_search_files(self, agent):
        """Test file search"""
        results = await agent.search("budget")
        
        assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_search_pdfs(self, agent):
        """Test PDF filter search"""
        results = await agent.search_pdfs()
        
        assert len(results) > 0
        assert all("pdf" in r.metadata["mime_type"] for r in results)
    
    @pytest.mark.asyncio
    async def test_share_file(self, agent):
        """Test sharing a file"""
        result = await agent.execute("share_file", {
            "file_id": "file-001",
            "email": "newuser@example.com",
            "permission": "view",
        })
        
        assert result.success
    
    @pytest.mark.asyncio
    async def test_create_folder(self, agent):
        """Test creating a folder"""
        result = await agent.execute("create_folder", {
            "name": "Test Folder",
        })
        
        assert result.success
        assert result.data["folder_id"]
    
    @pytest.mark.asyncio
    async def test_get_recent_files(self, agent):
        """Test getting recent files"""
        results = await agent.get_recent_files(days=30)
        
        assert len(results) > 0
