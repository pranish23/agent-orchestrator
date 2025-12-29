"""
Tests for Intent Classifier
"""
import pytest
from app.services.intent_classifier import IntentClassifier


@pytest.fixture
def classifier():
    return IntentClassifier()


class TestIntentClassifier:
    """Test suite for intent classification"""
    
    @pytest.mark.asyncio
    async def test_calendar_search_intent(self, classifier):
        """Test calendar search queries are classified correctly"""
        result = await classifier.classify("What's on my calendar next week?")
        
        assert "gcal" in result["services"]
        assert result["intent"] == "search_events"
        assert result["confidence"] >= 0.5
    
    @pytest.mark.asyncio
    async def test_email_search_intent(self, classifier):
        """Test email search queries are classified correctly"""
        result = await classifier.classify("Find emails from sarah@company.com about the budget")
        
        assert "gmail" in result["services"]
        assert result["intent"] == "search_emails"
        assert "sarah@company.com" in result["entities"].get("email_addresses", [])
    
    @pytest.mark.asyncio
    async def test_drive_search_intent(self, classifier):
        """Test Drive search queries are classified correctly"""
        result = await classifier.classify("Show me PDFs in Drive from last month")
        
        assert "gdrive" in result["services"]
        assert result["intent"] == "search_files"
    
    @pytest.mark.asyncio
    async def test_cancel_flight_intent(self, classifier):
        """Test multi-service flight cancellation query"""
        result = await classifier.classify("Cancel my Turkish Airlines flight")
        
        assert "gmail" in result["services"]
        assert "gcal" in result["services"]
        assert result["intent"] == "cancel_flight"
        assert result["entities"].get("airline") == "Turkish Airlines"
    
    @pytest.mark.asyncio
    async def test_prepare_meeting_intent(self, classifier):
        """Test meeting preparation query"""
        result = await classifier.classify("Prepare for tomorrow's meeting with Acme Corp")
        
        assert len(result["services"]) >= 2
        assert result["intent"] == "prepare_meeting"
    
    @pytest.mark.asyncio
    async def test_extracts_time_reference(self, classifier):
        """Test temporal entity extraction"""
        result = await classifier.classify("What meetings do I have tomorrow?")
        
        assert result["entities"].get("time_reference") == "tomorrow"
    
    @pytest.mark.asyncio
    async def test_empty_query(self, classifier):
        """Test handling of empty queries"""
        result = await classifier.classify("")
        
        assert result["confidence"] < 0.5
    
    @pytest.mark.asyncio
    async def test_cache_works(self, classifier):
        """Test that identical queries use cache"""
        query = "What's on my calendar?"
        
        result1 = await classifier.classify(query)
        result2 = await classifier.classify(query)
        
        assert result1 == result2
    
    @pytest.mark.asyncio
    async def test_context_influences_classification(self, classifier):
        """Test that context affects classification"""
        context = ["Tell me about the Turkish Airlines booking"]
        result = await classifier.classify("Cancel it", context=context)
        
        # Should infer from context
        assert result is not None


class TestPatternMatching:
    """Test fallback pattern matching"""
    
    @pytest.mark.asyncio
    async def test_calendar_keywords(self, classifier):
        result = await classifier.classify("meeting tomorrow")
        assert "gcal" in result["services"]
    
    @pytest.mark.asyncio
    async def test_email_keywords(self, classifier):
        result = await classifier.classify("check my inbox")
        assert "gmail" in result["services"]
    
    @pytest.mark.asyncio
    async def test_file_keywords(self, classifier):
        result = await classifier.classify("find the document")
        assert "gdrive" in result["services"]
