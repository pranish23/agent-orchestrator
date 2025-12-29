"""
Query Planner - Converts intents into execution DAGs
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import structlog

import json
import structlog
from app.config import settings
from app.services.tool_registry import ToolRegistry
from app.services.llm_provider import get_llm_provider

logger = structlog.get_logger()


class StepStatus(Enum):
    """Status of an execution step"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ExecutionStep:
    """A single step in the execution plan"""
    id: str
    service: str
    operation: str
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None
    
    def can_execute(self, completed_steps: set) -> bool:
        """Check if all dependencies are satisfied"""
        return all(dep in completed_steps for dep in self.depends_on)


@dataclass
class ExecutionPlan:
    """A complete execution plan (DAG) for a query"""
    query: str
    intent: str
    steps: List[ExecutionStep] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    
    def get_next_steps(self, completed: set) -> List[ExecutionStep]:
        """Get steps that can be executed now"""
        return [
            step for step in self.steps
            if step.status == StepStatus.PENDING and step.can_execute(completed)
        ]
    
    def mark_completed(self, step_id: str, result: Any = None):
        """Mark a step as completed"""
        for step in self.steps:
            if step.id == step_id:
                step.status = StepStatus.COMPLETED
                step.result = result
                break
    
    def mark_failed(self, step_id: str, error: str):
        """Mark a step as failed"""
        for step in self.steps:
            if step.id == step_id:
                step.status = StepStatus.FAILED
                step.error = error
                break


class QueryPlanner:
    """
    Creates execution plans from classified intents.
    
    Handles:
    - Parallel operations (independent searches)
    - Sequential dependencies (draft email needs search results)
    - Fallback strategies when data is missing
    """
    
    def __init__(self):
        self.logger = logger.bind(component="query_planner")
        self.registry = ToolRegistry()
        self.llm = get_llm_provider(settings) if settings else None
        
        # System prompt for the Architect LLM
        self.system_prompt = self._build_system_prompt()
    
    async def create_plan(
        self,
        query: str,
        intent: Dict[str, Any]
    ) -> ExecutionPlan:
        """
        Create an execution plan from a classified intent.
        
        Args:
            query: Original user query
            intent: Classified intent with services, steps, entities
            
        Returns:
            ExecutionPlan with steps and dependencies
        """
        intent_type = intent.get("intent", "general_search")
        services = intent.get("services", [])
        entities = intent.get("entities", {})
        
        self.logger.info(
            "Creating execution plan",
            intent=intent_type,
            services=services,
            entities=entities,
        )
        
        # Try LLM-based planning first if available and if intent is generic or complex
        # We fall back to templates only if LLM fails or isn't configured
        try:
            if self.llm:
                steps = await self._generate_plan_via_llm(query, intent)
                if steps:
                    self.logger.info("Generated plan via LLM", num_steps=len(steps))
                else:
                    self.logger.warning("LLM returned empty plan, falling back to templates")
                    steps = self._use_template_planner(query, intent_type, intent)
            else:
                steps = self._use_template_planner(query, intent_type, intent)
        except Exception as e:
            self.logger.error("LLM planning failed", error=str(e))
            steps = self._use_template_planner(query, intent_type, intent)
            
        return self._finalize_plan(query, intent_type, steps)

    def _use_template_planner(self, query: str, intent_type: str, intent: Dict) -> List[ExecutionStep]:
        """Fallback to template-based planning"""
        services = intent.get("services", [])
        is_simple_search = intent_type in ["search_emails", "search_events", "search_files", "general_search"]
        
        if len(services) > 1 and is_simple_search:
            plan_generator = self._plan_general_search
        else:
            plan_generator = self._get_plan_generator(intent_type)
            
        return plan_generator(query, intent)

    def _finalize_plan(self, query: str, intent_type: str, steps: List[ExecutionStep]) -> ExecutionPlan:
        """Finalize the plan structure"""
        # Build dependency groups for parallel execution
        parallel_groups = self._build_parallel_groups(steps)
        
        plan = ExecutionPlan(
            query=query,
            intent=intent_type,
            steps=steps,
            parallel_groups=parallel_groups,
        )
        
        self.logger.info(
            "Execution plan created",
            num_steps=len(steps),
            parallel_groups=len(parallel_groups),
        )
        
        return plan

    async def _generate_plan_via_llm(self, query: str, intent: Dict) -> List[ExecutionStep]:
        """Generate execution steps using the Architect LLM"""
        prompt = f"Query: {query}\nIntent: {json.dumps(intent, indent=2)}"
        
        response = await self.llm.chat_completion(
            prompt=prompt,
            system_prompt=self.system_prompt,
            response_format="json",
            temperature=0.0  # Deterministic planning
        )
        
        # Clean response of markdown formatting if present
        cleaned_response = response.strip()
        if cleaned_response.startswith("```json"):
            cleaned_response = cleaned_response[7:]
        if cleaned_response.startswith("```"):
            cleaned_response = cleaned_response[3:]
        if cleaned_response.endswith("```"):
            cleaned_response = cleaned_response[:-3]
        cleaned_response = cleaned_response.strip()
        
        try:
            plan_data = json.loads(cleaned_response)
            steps_data = plan_data.get("steps", [])
            
            steps = []
            for s in steps_data:
                tool_name = s.get("tool", "")
                if "_" in tool_name:
                    service, operation = tool_name.split("_", 1)
                    if service not in ["gmail", "gcal", "gdrive"]:
                         # Fallback/Error handling if service unknown, or trust LLM
                         pass
                else:
                    continue

                steps.append(ExecutionStep(
                    id=s.get("id"),
                    service=service,
                    operation=tool_name, 
                    params=s.get("parameters", {}),
                    depends_on=s.get("depends_on", [])
                ))
            
            # Post-processing to fix operation names for existing agents
            # Agents expect "search" not "gmail_search", so we map them if needed
            # Specifically, GCalAgent.search expects params, create_event etc.
            # We need to align the tool names with what agents expect
            
            for step in steps:
                # Map full tool name to agent operation
                if step.service == "gmail":
                     if step.operation == "gmail_search": step.operation = "search"
                     elif step.operation == "gmail_send_email": step.operation = "send_email"
                     elif step.operation == "gmail_create_draft": step.operation = "draft_email"
                elif step.service == "gcal":
                     if step.operation == "gcal_search_events": step.operation = "search"
                     elif step.operation == "gcal_create_event": step.operation = "create_event"
                elif step.service == "gdrive":
                     if step.operation == "gdrive_search_files": step.operation = "search"
                     elif step.operation == "gdrive_create_file": step.operation = "create_file"
                     elif step.operation == "gdrive_share_file": step.operation = "share_file"
                    
            return steps
            
        except json.JSONDecodeError:
            self.logger.error("Failed to parse LLM plan JSON")
            return None

    def _build_system_prompt(self) -> str:
        """Construct the system prompt with tool definitions"""
        tools_schema = json.dumps(self.registry.get_all_schemas(), indent=2)
        
        return f"""You are the Architect Agent. Your goal is to create an efficient execution plan for a user query.
You have access to the following tools:

{tools_schema}

INSTRUCTIONS:
1. Analyze the user's query and the classified intent.
2. Break down the request into a series of logical steps.
3. Use the provided tools to accomplish each step.
4. DETERMINE DEPENDENCIES correctly. If Step B needs information from Step A, Step B must depend on Step A.
5. OPTIMIZE FOR PARALLELISM. Steps that do not depend on each other should have empty dependencies or depend on the same parent.

OUTPUT FORMAT:
Return a JSON object with a "steps" array. Each step must have:
- "id": unique string identifier (e.g., "search_email")
- "tool": the exact name of the tool to use (e.g., "gmail_search")
- "parameters": arguments for the tool
- "depends_on": array of step IDs that must complete before this step starts
""" 
    
    def _get_plan_generator(self, intent_type: str):
        """Get the appropriate plan generator for an intent"""
        generators = {
            "cancel_flight": self._plan_cancel_flight,
            "prepare_meeting": self._plan_prepare_meeting,
            "search_emails": self._plan_search_emails,
            "search_events": self._plan_search_events,
            "schedule_event": self._plan_schedule_event,
            "search_files": self._plan_search_files,
            "draft_email": self._plan_draft_email,
            "general_search": self._plan_general_search,
        }
        return generators.get(intent_type, self._plan_general_search)

    def _plan_cancel_flight(self, query: str, intent: Dict) -> List[ExecutionStep]:
        """Plan for canceling a flight booking"""
        entities = intent.get("entities", {})
        airline = entities.get("airline", "")
        
        return [
            # Step 1: Search Gmail for booking (parallel)
            ExecutionStep(
                id="search_booking_email",
                service="gmail",
                operation="search",
                params={"query": f"{airline} booking confirmation", "limit": 5},
                depends_on=[],
            ),
            # Step 2: Search Calendar for flight event (parallel with step 1)
            ExecutionStep(
                id="find_flight_event",
                service="gcal",
                operation="search",
                params={"query": f"{airline} flight", "limit": 5},
                depends_on=[],
            ),
            # Step 3: Draft cancellation email (depends on step 1)
            ExecutionStep(
                id="draft_cancellation",
                service="gmail",
                operation="draft_email",
                params={
                    "to": ["support@airline.com"],
                    "subject": "Flight Cancellation Request",
                    "body": "Please cancel my booking...",
                },
                depends_on=["search_booking_email"],
            ),
        ]

    def _plan_schedule_event(self, query: str, intent: Dict) -> List[ExecutionStep]:
        """Plan for scheduling a calendar event with conflict checks"""
        entities = intent.get("entities", {})
        
        # 1. Parse Start Time
        time_str = entities.get("time_reference") or entities.get("date") or entities.get("start_time")
        # Default to tomorrow 9am if parsing fails
        start_time = self._parse_datetime(time_str)
        if not start_time:
            start_time = (datetime.now() + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
            
        # 2. Calculate End Time (default 1 hour)
        end_time = start_time + timedelta(hours=1)
        
        # 3. Construct Title (Jhon Doe -> Meeting with Jhon Doe)
        title = entities.get("event_type", "Meeting")
        if person := (entities.get("person") or entities.get("attendees", [""])[0]):
            if "meeting" not in title.lower():
                title = f"{title} with {person}"
        
        return [
            # Step 1: Check Calendar Availability (Parallel)
            ExecutionStep(
                id="check_calendar",
                service="gcal",
                operation="search",
                params={
                    "query": "",
                    "filters": {
                        "start_after": start_time.replace(hour=0, minute=0).isoformat(),
                        "start_before": (start_time + timedelta(days=1)).replace(hour=0, minute=0).isoformat(),
                    },
                    "limit": 10
                },
                depends_on=[],
            ),
            # Step 2: Check OOO Documents (Parallel)
            ExecutionStep(
                id="check_ooo_doc",
                service="gdrive",
                operation="search",
                params={
                    "query": "out of office schedule",
                    "limit": 3
                },
                depends_on=[],
            ),
            # Step 3: Create Event (Run in parallel but synthesis will check results)
            ExecutionStep(
                id="create_event",
                service="gcal",
                operation="create_event",
                params={
                    "title": title,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "attendees": entities.get("attendees", []),
                    "description": query,
                },
                depends_on=[],
            ),
        ]

    def _parse_datetime(self, time_str: Optional[str]) -> Optional[datetime]:
        """Parse entity date string to datetime"""
        if not time_str:
            return None
            
        try:
            # Try simple ISO 'YYYY-MM-DD'
            return datetime.strptime(time_str, "%Y-%m-%d").replace(hour=9, minute=0)
        except ValueError:
            pass
            
        try:
            # Try 'January 16, 2026'
            return datetime.strptime(time_str, "%B %d, %Y").replace(hour=9, minute=0)
        except ValueError:
            pass
            
        try:
            # Try ISO with time
            return datetime.fromisoformat(time_str)
        except ValueError:
            pass
            
        return None

    def _plan_prepare_meeting(self, query: str, intent: Dict) -> List[ExecutionStep]:
        """Plan for preparing for a meeting"""
        entities = intent.get("entities", {})
        company = entities.get("company", "")
        
        steps = [
            # Step 1: Find the meeting (required first)
            ExecutionStep(
                id="find_meeting",
                service="gcal",
                operation="search",
                params={"query": f"meeting {company}", "limit": 5},
                depends_on=[],
            ),
            # Step 2: Search related emails (parallel with step 3)
            ExecutionStep(
                id="search_related_emails",
                service="gmail",
                operation="search",
                params={"query": company, "limit": 10},
                depends_on=[],
            ),
            # Step 3: Search related documents (parallel with step 2)
            ExecutionStep(
                id="search_related_docs",
                service="gdrive",
                operation="search",
                params={"query": company, "limit": 10},
                depends_on=[],
            ),
        ]

        # Check for document creation request
        if doc_name := (entities.get("document_name") or entities.get("file_name")):
            steps.append(
                ExecutionStep(
                    id="create_meeting_doc",
                    service="gdrive",
                    operation="create_file",
                    params={
                        "name": doc_name,
                        "mime_type": "application/vnd.google-apps.document",
                        "content": f"Meeting Notes - {company}\nDate: {datetime.now().strftime('%Y-%m-%d')}\n\nAgenda:\n1. ",
                    },
                    depends_on=[],
                )
            )
            
        return steps
    
    def _plan_search_emails(self, query: str, intent: Dict) -> List[ExecutionStep]:
        """Plan for searching emails"""
        entities = intent.get("entities", {})
        
        params = {"query": query, "limit": 10}
        if emails := entities.get("email_addresses"):
            params["filters"] = {"sender": emails[0]}
        
        return [
            ExecutionStep(
                id="search_emails",
                service="gmail",
                operation="search",
                params=params,
                depends_on=[],
            ),
        ]
    
    def _plan_search_events(self, query: str, intent: Dict) -> List[ExecutionStep]:
        """Plan for searching calendar events"""
        entities = intent.get("entities", {})
        
        params = {"query": query, "limit": 20}
        filters = {}
        
        # Handle time reference
        time_ref = entities.get("time_reference") or entities.get("time_frame") or entities.get("date_range")
        if time_ref:
            start, end = self._get_date_range(time_ref)
            if start:
                filters["start_after"] = start.isoformat() if hasattr(start, 'isoformat') else start
            if end:
                filters["start_before"] = end.isoformat() if hasattr(end, 'isoformat') else end
                
        if emails := entities.get("email_addresses"):
            filters["attendee"] = emails[0]
            
        if filters:
            params["filters"] = filters
        
        return [
            ExecutionStep(
                id="search_events",
                service="gcal",
                operation="search",
                params=params,
                depends_on=[],
            ),
        ]
    
    def _plan_search_files(self, query: str, intent: Dict) -> List[ExecutionStep]:
        """Plan for searching Drive files"""
        entities = intent.get("entities", {})
        
        params = {"query": query, "limit": 10}
        
        # Check for file type in query
        query_lower = query.lower()
        filters = {}
        if "pdf" in query_lower:
            filters["file_type"] = "pdf"
        elif "doc" in query_lower:
            filters["file_type"] = "doc"
        elif "sheet" in query_lower or "excel" in query_lower:
            filters["file_type"] = "sheet"
            
        if filters:
            params["filters"] = filters
        
        return [
            ExecutionStep(
                id="search_files",
                service="gdrive",
                operation="search",
                params=params,
                depends_on=[],
            ),
        ]
        
    def _plan_draft_email(self, query: str, intent: Dict) -> List[ExecutionStep]:
        """Plan for drafting an email"""
        entities = intent.get("entities", {})
        
        return [
            ExecutionStep(
                id="draft_email",
                service="gmail",
                operation="draft_email",
                params={
                    "to": entities.get("email_addresses", []),
                    "subject": "Draft",
                    "body": "",
                },
                depends_on=[],
            ),
        ]

    def _plan_general_search(self, query: str, intent: Dict) -> List[ExecutionStep]:
        """Generic search across all relevant services with smart filtering"""
        services = intent.get("services") or ["gmail", "gcal", "gdrive"]
        entities = intent.get("entities") or {}
        steps = []
        
        # Calculate common filters
        common_filters = {}
        
        # Date filtering
        time_ref = entities.get("time_reference") or entities.get("time_frame") or entities.get("date_range")
        if time_ref:
            start, end = self._get_date_range(time_ref)
            if start:
                common_filters["start_after"] = start.isoformat() if hasattr(start, 'isoformat') else start
                common_filters["from_date"] = start 
            if end:
                common_filters["start_before"] = end.isoformat() if hasattr(end, 'isoformat') else end
                common_filters["to_date"] = end
        
        # Email entities (sender/attendee)
        emails = entities.get("email_addresses", [])
        
        for service in services:
            operation_map = {
                "gmail": "search",
                "gcal": "search",
                "gdrive": "search",
            }
            
            # Service-specific params
            params = {"query": query, "limit": 5, "filters": {}}
            
            # Apply filters
            if service == "gcal":
                if "start_after" in common_filters:
                    params["filters"]["start_after"] = common_filters["start_after"]
                if "start_before" in common_filters:
                    params["filters"]["start_before"] = common_filters["start_before"]
                if emails:
                    params["filters"]["attendee"] = emails[0]
                    
            elif service == "gmail":
                if "from_date" in common_filters:
                    params["filters"]["from_date"] = common_filters["from_date"]
                if "to_date" in common_filters:
                    params["filters"]["to_date"] = common_filters["to_date"]
                if emails:
                    params["filters"]["sender"] = emails[0]
                    
            elif service == "gdrive":
                query_lower = query.lower()
                if "pdf" in query_lower:
                    params["filters"]["file_type"] = "pdf"
                elif "doc" in query_lower:
                    params["filters"]["file_type"] = "doc"
                elif "sheet" in query_lower:
                    params["filters"]["file_type"] = "sheet"
                
                # Drive also supports modified date if needed
                if "from_date" in common_filters:
                    params["filters"]["modified_after"] = common_filters["from_date"]

            steps.append(
                ExecutionStep(
                    id=f"search_{service}",
                    service=service,
                    operation=operation_map.get(service, "search"),
                    params=params,
                    depends_on=[],
                )
            )
        
        return steps

    def _get_date_range(self, time_ref: str) -> tuple[Optional[datetime], Optional[datetime]]:
        """Convert time reference string to date range"""
        from datetime import datetime, timedelta
        
        now = datetime.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        start, end = None, None
        if time_ref == "today":
            start, end = today, today + timedelta(days=1)
        elif time_ref == "tomorrow":
            start, end = today + timedelta(days=1), today + timedelta(days=2)
        elif time_ref == "yesterday":
            start, end = today - timedelta(days=1), today
        elif "next week" in time_ref:
            start, end = today, today + timedelta(days=7)
        elif "this week" in time_ref:
            start, end = today, today + timedelta(days=7)
        elif "last week" in time_ref:
            start, end = today - timedelta(days=7), today
        elif "month" in time_ref:
            start, end = today, today + timedelta(days=30)
            
        self.logger.info("Calculated date range", time_ref=time_ref, start=start.isoformat() if start else None, end=end.isoformat() if end else None)
        return start, end
    
    def _build_parallel_groups(self, steps: List[ExecutionStep]) -> List[List[str]]:
        """
        Build groups of steps that can run in parallel.
        
        Returns list of lists, where each inner list contains step IDs
        that can run simultaneously.
        """
        groups = []
        completed = set()
        remaining = {step.id: step for step in steps}
        
        while remaining:
            # Find all steps that can run now
            runnable = [
                step_id for step_id, step in remaining.items()
                if step.can_execute(completed)
            ]
            
            if not runnable:
                # Shouldn't happen with valid DAGs, but handle it
                self.logger.warning("No runnable steps but remaining exists")
                break
            
            groups.append(runnable)
            
            # Mark as completed and remove from remaining
            for step_id in runnable:
                completed.add(step_id)
                del remaining[step_id]
        
        return groups
