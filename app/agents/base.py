"""
Base agent interface for all service agents
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import structlog

logger = structlog.get_logger()


@dataclass
class SearchResult:
    """Generic search result from any agent"""
    id: str
    title: str
    preview: str
    metadata: Dict[str, Any]
    relevance_score: float = 0.0


@dataclass
class OperationResult:
    """Result of an agent operation"""
    success: bool
    operation: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Abstract base class for service agents.
    
    All agents (Gmail, GCal, Drive) implement this interface to ensure
    consistent behavior across the orchestration layer.
    """
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.service_name: str = "base"
        self.logger = logger.bind(agent=self.service_name, user_id=user_id)
    
    @abstractmethod
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Search for items matching the query.
        
        Args:
            query: Natural language or keyword query
            filters: Optional filters (date range, sender, etc.)
            limit: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        pass
    
    @abstractmethod
    async def execute(
        self,
        operation: str,
        params: Dict[str, Any]
    ) -> OperationResult:
        """
        Execute a write operation.
        
        Args:
            operation: Operation name (send, create, delete, etc.)
            params: Operation parameters
            
        Returns:
            OperationResult indicating success/failure
        """
        pass
    
    @abstractmethod
    async def get_context(
        self,
        item_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get full context/content for an item.
        
        Args:
            item_id: Unique identifier for the item
            
        Returns:
            Full item data for LLM reasoning
        """
        pass
    
    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get a single item by ID (alias for get_context)"""
        return await self.get_context(item_id)
    
    def _log_operation(self, operation: str, **kwargs):
        """Log an operation with context"""
        self.logger.info(
            f"Agent operation: {operation}",
            operation=operation,
            **kwargs
        )
