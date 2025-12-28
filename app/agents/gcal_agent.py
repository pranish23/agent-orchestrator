"""
Mock Google Calendar Agent for development and testing
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.agents.base import BaseAgent, SearchResult, OperationResult


# Mock calendar events
MOCK_EVENTS = [
    {
        "id": "event-001",
        "calendar_id": "primary",
        "title": "Istanbul → NYC Flight (TK1234)",
        "description": "Turkish Airlines flight. Booking ref: ABC123",
        "location": "Istanbul Airport (IST)",
        "start_time": datetime.now() + timedelta(days=10, hours=10, minutes=30),
        "end_time": datetime.now() + timedelta(days=10, hours=22),
        "attendees": ["user@example.com"],
    },
    {
        "id": "event-002",
        "calendar_id": "primary",
        "title": "Q4 Budget Review Meeting",
        "description": "Review Q4 budget with finance team. Prepare slides.",
        "location": "Conference Room A",
        "start_time": datetime.now() + timedelta(days=1, hours=14),
        "end_time": datetime.now() + timedelta(days=1, hours=15),
        "attendees": ["user@example.com", "sarah@company.com", "cfo@company.com"],
    },
    {
        "id": "event-003",
        "calendar_id": "primary",
        "title": "Client Meeting - Acme Corp",
        "description": "Partnership discussion with Acme Corp. Review proposal.",
        "location": "Zoom: https://zoom.us/j/123456789",
        "start_time": datetime.now() + timedelta(days=1, hours=10),
        "end_time": datetime.now() + timedelta(days=1, hours=11),
        "attendees": ["user@example.com", "john.smith@acmecorp.com"],
    },
    {
        "id": "event-004",
        "calendar_id": "primary",
        "title": "Team Standup",
        "description": "Daily standup meeting",
        "location": "Slack Huddle",
        "start_time": datetime.now() + timedelta(days=1, hours=9),
        "end_time": datetime.now() + timedelta(days=1, hours=9, minutes=15),
        "attendees": ["user@example.com", "team@company.com"],
    },
    {
        "id": "event-005",
        "calendar_id": "primary",
        "title": "Sprint Planning",
        "description": "Plan next sprint. Review backlog.",
        "location": "Conference Room B",
        "start_time": datetime.now() + timedelta(days=4, hours=14),
        "end_time": datetime.now() + timedelta(days=4, hours=16),
        "attendees": ["user@example.com", "team@company.com", "manager@company.com"],
    },
    {
        "id": "event-006",
        "calendar_id": "primary",
        "title": "Dentist Appointment",
        "description": "Regular checkup",
        "location": "123 Medical Center, Suite 456",
        "start_time": datetime.now() + timedelta(days=7, hours=11),
        "end_time": datetime.now() + timedelta(days=7, hours=12),
        "attendees": ["user@example.com"],
    },
    {
        "id": "event-007",
        "calendar_id": "primary",
        "title": "Meeting with John",
        "description": "Discuss project timeline",
        "location": "Office",
        "start_time": datetime.now() + timedelta(days=2, hours=15),
        "end_time": datetime.now() + timedelta(days=2, hours=16),
        "attendees": ["user@example.com", "john@company.com"],
    },
    {
        "id": "event-008",
        "calendar_id": "primary",
        "title": "Meeting with John Miller",
        "description": "HR review",
        "location": "HR Office",
        "start_time": datetime.now() + timedelta(days=3, hours=10),
        "end_time": datetime.now() + timedelta(days=3, hours=10, minutes=30),
        "attendees": ["user@example.com", "john.miller@company.com"],
    },
]


class GCalAgent(BaseAgent):
    """
    Mock Google Calendar agent for development.
    
    Implements event search, creation, update, and deletion.
    Uses in-memory mock data instead of actual Calendar API.
    """
    
    def __init__(self, user_id: str, search_service: Optional[Any] = None):
        super().__init__(user_id)
        self.service_name = "gcal"
        self.search_service = search_service
        self._events = MOCK_EVENTS.copy()
    
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Search calendar events by keyword, date range, attendee, etc.
        """
        self._log_operation("search_events", query=query, filters=filters)
        
        # Use SearchService if available
        if self.search_service:
            try:
                hits = await self.search_service.search(
                    query=query,
                    user_id=self.user_id,
                    services=["gcal"],
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
        
        query_words = [w for w in query_lower.split() if len(w) > 3]
        
        for event in self._events:
            match_score = 0
            
            # Keyword matching
            for word in query_words:
                if word in event["title"].lower() or (event.get("description") and word in event["description"].lower()):
                    match_score += 0.2
            
            if query_lower and query_lower in event["title"].lower():
                match_score += 0.5
            
            # Filter by attendee
            attendee_match = True
            if filters.get("attendee"):
                attendee_filter = filters["attendee"].lower()
                if not any(attendee_filter in att.lower() for att in event["attendees"]):
                    attendee_match = False
            
            if not attendee_match:
                continue
            
            # Filter by date range
            if filters.get("start_after"):
                if event["start_time"] < filters["start_after"]:
                    continue
            if filters.get("start_before"):
                if event["start_time"] > filters["start_before"]:
                    continue
            
            # If we have filters but no query match, or if the query is empty
            is_generic_query = any(kw in query_lower for kw in ["calendar", "schedule", "events", "meeting"])
            
            if match_score > 0 or not query_words or (attendee_match and filters.get("attendee")) or is_generic_query:
                results.append(SearchResult(
                    id=event["id"],
                    title=event["title"],
                    preview=f"{event['start_time'].strftime('%b %d, %I:%M %p')} - {event.get('location', 'No location')}",
                    metadata={
                        "start_time": event["start_time"].isoformat(),
                        "end_time": event["end_time"].isoformat(),
                        "location": event.get("location"),
                        "attendees": event["attendees"],
                    },
                    relevance_score=max(match_score, 0.1),
                ))
        
        # Sort by start time for calendar queries
        results.sort(key=lambda x: x.metadata["start_time"])
        return results[:limit]
    
    async def execute(
        self,
        operation: str,
        params: Dict[str, Any]
    ) -> OperationResult:
        """
        Execute Calendar operations: create, update, delete.
        """
        self._log_operation(operation, params=params)
        
        if operation == "create_event":
            return await self._create_event(params)
        elif operation == "update_event":
            return await self._update_event(params)
        elif operation == "delete_event":
            return await self._delete_event(params)
        else:
            return OperationResult(
                success=False,
                operation=operation,
                error=f"Unknown operation: {operation}"
            )
    
    async def _create_event(self, params: Dict[str, Any]) -> OperationResult:
        """Create a new calendar event"""
        required = ["title", "start_time", "end_time"]
        for field in required:
            if field not in params:
                return OperationResult(
                    success=False,
                    operation="create_event",
                    error=f"Missing required field: {field}"
                )
        
        event_id = f"event-{uuid4().hex[:8]}"
        
        # Parse datetimes if strings
        start = params["start_time"]
        if isinstance(start, str):
            start = datetime.fromisoformat(start)
            
        end = params["end_time"]
        if isinstance(end, str):
            end = datetime.fromisoformat(end)
            
        new_event = {
            "id": event_id,
            "calendar_id": "primary",
            "title": params["title"],
            "description": params.get("description", ""),
            "location": params.get("location", ""),
            "start_time": start,
            "end_time": end,
            "attendees": params.get("attendees", ["user@example.com"]),
        }
        self._events.append(new_event)
        
        return OperationResult(
            success=True,
            operation="create_event",
            data={
                "event_id": event_id,
                "title": params["title"],
                "message": "Event created successfully",
            }
        )
    
    async def _update_event(self, params: Dict[str, Any]) -> OperationResult:
        """Update an existing event"""
        event_id = params.get("event_id")
        if not event_id:
            return OperationResult(
                success=False,
                operation="update_event",
                error="Missing event_id"
            )
        
        for event in self._events:
            if event["id"] == event_id:
                for key, value in params.items():
                    if key != "event_id" and key in event:
                        event[key] = value
                return OperationResult(
                    success=True,
                    operation="update_event",
                    data={"event_id": event_id, "message": "Event updated successfully"}
                )
        
        return OperationResult(
            success=False,
            operation="update_event",
            error=f"Event not found: {event_id}"
        )
    
    async def _delete_event(self, params: Dict[str, Any]) -> OperationResult:
        """Delete a calendar event"""
        event_id = params.get("event_id")
        if not event_id:
            return OperationResult(
                success=False,
                operation="delete_event",
                error="Missing event_id"
            )
        
        for i, event in enumerate(self._events):
            if event["id"] == event_id:
                self._events.pop(i)
                return OperationResult(
                    success=True,
                    operation="delete_event",
                    data={"event_id": event_id, "message": "Event deleted successfully"}
                )
        
        return OperationResult(
            success=False,
            operation="delete_event",
            error=f"Event not found: {event_id}"
        )
    
    async def get_context(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get full event details"""
        for event in self._events:
            if event["id"] == item_id:
                return {
                    **event,
                    "start_time": event["start_time"].isoformat(),
                    "end_time": event["end_time"].isoformat(),
                }
        return None
    
    async def get_events_next_week(self, limit: int = 20) -> List[SearchResult]:
        """Get all events in the next 7 days"""
        now = datetime.now()
        next_week = now + timedelta(days=7)
        return await self.search("", filters={
            "start_after": now,
            "start_before": next_week,
        }, limit=limit)
    
    async def get_events_by_attendee(self, email: str, limit: int = 10) -> List[SearchResult]:
        """Get events with a specific attendee"""
        return await self.search("", filters={"attendee": email}, limit=limit)
