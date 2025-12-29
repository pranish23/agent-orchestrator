"""
Mock Gmail Agent for development and testing
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4
import random

from app.agents.base import BaseAgent, SearchResult, OperationResult


# Mock email data for testing
MOCK_EMAILS = [
    {
        "id": "email-001",
        "thread_id": "thread-001",
        "subject": "Turkish Airlines Booking Confirmation - TK1234",
        "sender": "booking@turkishairlines.com",
        "recipients": ["user@example.com"],
        "body": """Dear Passenger,

Your booking has been confirmed.

Flight: TK1234
Route: Istanbul (IST) → New York (JFK)
Date: November 5, 2024
Departure: 10:30 AM
Booking Reference: ABC123

Thank you for flying with Turkish Airlines.
""",
        "labels": ["inbox", "travel"],
        "received_at": datetime.now() - timedelta(days=21),
    },
    {
        "id": "email-002",
        "thread_id": "thread-002",
        "subject": "Q4 Budget Review Meeting",
        "sender": "sarah@company.com",
        "recipients": ["user@example.com", "team@company.com"],
        "body": """Hi team,

Please find attached the Q4 budget review documents. Let's discuss in tomorrow's meeting.

Key points:
- Revenue up 15%
- Marketing spend needs review
- New hires for Q1

Best,
Sarah
""",
        "labels": ["inbox", "work", "important"],
        "received_at": datetime.now() - timedelta(days=7),
    },
    {
        "id": "email-003",
        "thread_id": "thread-003",
        "subject": "Acme Corp - Partnership Proposal",
        "sender": "john.smith@acmecorp.com",
        "recipients": ["user@example.com"],
        "body": """Dear Partner,

Following our meeting last week, I'm pleased to share our partnership proposal.

The attached document outlines our proposed collaboration on the Widget X project.

Looking forward to our meeting tomorrow to discuss further.

Best regards,
John Smith
VP of Partnerships, Acme Corp
""",
        "labels": ["inbox", "clients"],
        "received_at": datetime.now() - timedelta(days=2),
    },
    {
        "id": "email-004",
        "thread_id": "thread-004",
        "subject": "Weekly Team Update",
        "sender": "manager@company.com",
        "recipients": ["user@example.com", "team@company.com"],
        "body": """Team,

Here's the weekly update:

Completed this week:
- Feature A launched
- Bug fixes in production
- Client presentation done

Next week:
- Sprint planning
- Q4 roadmap review

Have a great weekend!
""",
        "labels": ["inbox", "work"],
        "received_at": datetime.now() - timedelta(days=3),
    },
    {
        "id": "email-005",
        "thread_id": "thread-005",
        "subject": "Invoice #12345 - Payment Due",
        "sender": "billing@vendor.com",
        "recipients": ["user@example.com"],
        "body": """Invoice Details:

Invoice Number: 12345
Amount: $5,000.00
Due Date: December 1, 2024

Please remit payment at your earliest convenience.

Thank you for your business.
""",
        "labels": ["inbox", "finance"],
        "received_at": datetime.now() - timedelta(days=5),
    },
]

# Store for drafts
MOCK_DRAFTS = {}


class GmailAgent(BaseAgent):
    """
    Mock Gmail agent for development.
    
    Implements email search, reading, drafting, and sending.
    Uses in-memory mock data instead of actual Gmail API.
    """
    
    def __init__(self, user_id: str, search_service: Optional[Any] = None):
        super().__init__(user_id)
        self.service_name = "gmail"
        self.search_service = search_service
        self._emails = MOCK_EMAILS.copy()
    
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Search emails by keyword, sender, date range, etc.
        """
        self._log_operation("search_emails", query=query, filters=filters)
        
        # Use SearchService if available
        if self.search_service:
            try:
                hits = await self.search_service.search(
                    query=query,
                    user_id=self.user_id,
                    services=["gmail"],
                    filters=filters,
                    limit=limit
                )
                return [
                    SearchResult(
                        id=hit.id,
                        title=hit.title,
                        preview=hit.preview,
                        metadata=hit.metadata,
                        relevance_score=hit.final_score
                    )
                    for hit in hits
                ]
            except Exception as e:
                self.logger.error("SearchService failed, falling back to mock", error=str(e))
        
        results = []
        query_lower = query.lower()
        filters = filters or {}
        
        # Simple keywords for matching instead of full query
        query_words = [w for w in query_lower.split() if len(w) > 3]
        
        for email in self._emails:
            # Keyword matching
            match_score = 0
            
            # If query is empty but we have filters, we might still match
            has_keyword_match = False
            for word in query_words:
                if word in email["subject"].lower() or word in email["body"].lower() or word in email["sender"].lower():
                    match_score += 0.2
                    has_keyword_match = True
            
            # Direct match score
            if query_lower and query_lower in email["subject"].lower():
                match_score += 0.5
            
            # Filter by sender
            sender_match = True
            if filters.get("sender"):
                if filters["sender"].lower() not in email["sender"].lower():
                    sender_match = False
            
            if not sender_match:
                continue
            
            # Filter by date range
            if filters.get("from_date"):
                if email["received_at"] < filters["from_date"]:
                    continue
            if filters.get("to_date"):
                if email["received_at"] > filters["to_date"]:
                    continue
            
            # Filter by labels
            if filters.get("labels"):
                if not any(label in email["labels"] for label in filters["labels"]):
                    continue
            
            # If sender matches and there's no query, or if there's a keyword match
            if match_score > 0 or not query_words or (filters.get("sender") and sender_match):
                results.append(SearchResult(
                    id=email["id"],
                    title=email["subject"],
                    preview=email["body"][:200] + "...",
                    metadata={
                        "sender": email["sender"],
                        "received_at": email["received_at"].isoformat(),
                        "labels": email["labels"],
                    },
                    relevance_score=max(match_score, 0.1),
                ))
        
        # Sort by relevance
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:limit]
    
    async def execute(
        self,
        operation: str,
        params: Dict[str, Any]
    ) -> OperationResult:
        """
        Execute Gmail operations: send, draft, update_labels.
        """
        self._log_operation(operation, params=params)
        
        if operation == "send_email":
            return await self._send_email(params)
        elif operation == "draft_email":
            return await self._draft_email(params)
        elif operation == "update_labels":
            return await self._update_labels(params)
        else:
            return OperationResult(
                success=False,
                operation=operation,
                error=f"Unknown operation: {operation}"
            )
    
    async def _send_email(self, params: Dict[str, Any]) -> OperationResult:
        """Send an email"""
        required = ["to", "subject", "body"]
        for field in required:
            if field not in params:
                return OperationResult(
                    success=False,
                    operation="send_email",
                    error=f"Missing required field: {field}"
                )
        
        email_id = f"email-{uuid4().hex[:8]}"
        return OperationResult(
            success=True,
            operation="send_email",
            data={
                "email_id": email_id,
                "to": params["to"],
                "subject": params["subject"],
                "message": "Email sent successfully",
            }
        )
    
    async def _draft_email(self, params: Dict[str, Any]) -> OperationResult:
        """Create an email draft"""
        required = ["to", "subject", "body"]
        for field in required:
            if field not in params:
                return OperationResult(
                    success=False,
                    operation="draft_email",
                    error=f"Missing required field: {field}"
                )
        
        draft_id = f"draft-{uuid4().hex[:8]}"
        MOCK_DRAFTS[draft_id] = {
            "id": draft_id,
            "to": params["to"],
            "subject": params["subject"],
            "body": params["body"],
            "created_at": datetime.now(),
        }
        
        return OperationResult(
            success=True,
            operation="draft_email",
            data={
                "draft_id": draft_id,
                "to": params["to"],
                "subject": params["subject"],
                "message": "Draft created successfully",
            }
        )
    
    async def _update_labels(self, params: Dict[str, Any]) -> OperationResult:
        """Update labels on an email"""
        email_id = params.get("email_id")
        if not email_id:
            return OperationResult(
                success=False,
                operation="update_labels",
                error="Missing email_id"
            )
        
        return OperationResult(
            success=True,
            operation="update_labels",
            data={
                "email_id": email_id,
                "labels": params.get("labels", []),
                "message": "Labels updated successfully",
            }
        )
    
    async def get_context(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get full email content"""
        for email in self._emails:
            if email["id"] == item_id:
                return {
                    **email,
                    "received_at": email["received_at"].isoformat(),
                }
        return None
    
    async def search_by_sender(self, sender: str, limit: int = 10) -> List[SearchResult]:
        """Convenience method to search by sender"""
        return await self.search("", filters={"sender": sender}, limit=limit)
    
    async def get_recent_emails(self, days: int = 7, limit: int = 10) -> List[SearchResult]:
        """Get recent emails from the last N days"""
        from_date = datetime.now() - timedelta(days=days)
        return await self.search("", filters={"from_date": from_date}, limit=limit)
