"""
Tests for the Orchestrator Service
"""
import pytest
from uuid import uuid4
from unittest.mock import MagicMock, AsyncMock
from app.services.orchestrator import Orchestrator
from app.services.intent_classifier import IntentClassifier
from app.services.query_planner import QueryPlanner
from app.services.response_synthesizer import ResponseSynthesizer


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def orchestrator(mock_db):
    return Orchestrator(mock_db)


class TestOrchestrator:
    """Test suite for the main Orchestrator"""

    @pytest.mark.asyncio
    async def test_process_simple_query(self, orchestrator):
        """Test full processing of a simple calendar query"""
        query = "What's on my calendar next week?"
        conversation_id = uuid4()
        
        # Test the process method
        # Note: This will use the mock agents and pattern matching fallback
        result = await orchestrator.process(query, conversation_id=conversation_id)
        
        assert result is not None
        assert "response" in result
        assert result["intent"]["intent"] == "search_events"
        assert "gcal" in result["intent"]["services"]

    @pytest.mark.asyncio
    async def test_process_multi_service_query(self, orchestrator):
        """Test orchestration across multiple services (flight cancellation)"""
        query = "Cancel my Turkish Airlines flight"
        conversation_id = uuid4()
        
        result = await orchestrator.process(query, conversation_id=conversation_id)
        
        assert result is not None
        # Should have interacted with gmail and gcal
        assert "gmail" in result["intent"]["services"]
        assert "gcal" in result["intent"]["services"]
        assert result["intent"]["intent"] == "cancel_flight"

    @pytest.mark.asyncio
    async def test_process_meeting_prep(self, orchestrator):
        """Test meeting preparation orchestration (all services)"""
        query = "Prepare for tomorrow's meeting with Acme Corp"
        conversation_id = uuid4()
        
        result = await orchestrator.process(query, conversation_id=conversation_id)
        
        assert result is not None
        assert result["intent"]["intent"] == "prepare_meeting"
        # Often involves all 3
        assert len(result["intent"]["services"]) >= 2

    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, mock_db):
        """Test that orchestrator initializes its sub-services"""
        orchestrator = Orchestrator(mock_db)
        
        assert isinstance(orchestrator.intent_classifier, IntentClassifier)
        assert isinstance(orchestrator.query_planner, QueryPlanner)
        assert isinstance(orchestrator.response_synthesizer, ResponseSynthesizer)

    @pytest.mark.asyncio
    async def test_execution_with_empty_plan(self, orchestrator):
        """Test handling of queries that result in no steps"""
        query = "just some random text"
        conversation_id = uuid4()
        
        # Pattern matcher might return general_search with no specific steps
        # or simple search steps. 
        result = await orchestrator.process(query, conversation_id=conversation_id)
        
        assert result is not None
        assert "response" in result

    @pytest.mark.asyncio
    async def test_error_handling_in_process(self, orchestrator):
        """Test that orchestrator catches and reports service errors"""
        # Force an error by passing None where a string is expected
        # The process method catches all exceptions and returns an error message
        result = await orchestrator.process(None, conversation_id=uuid4())
        
        assert result is not None
        assert "encountered an error" in result["response"]
        assert result["intent"] is None

    @pytest.mark.asyncio
    async def test_context_persistence(self, orchestrator):
        """Test that conversation context is passed to classifier"""
        query = "and the other one"
        conversation_id = uuid4()
        
        # This will use the cache service to store/retrieve context
        result = await orchestrator.process(
            query, 
            conversation_id=conversation_id
        )
        
        assert result is not None
