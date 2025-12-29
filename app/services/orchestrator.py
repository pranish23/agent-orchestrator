"""
Orchestrator - Main coordination layer for query execution
"""
import asyncio
from typing import Any, Dict, List, Optional
from uuid import UUID
from datetime import datetime
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.agents import GmailAgent, GCalAgent, DriveAgent
from app.services.intent_classifier import IntentClassifier
from app.services.query_planner import QueryPlanner, ExecutionPlan, StepStatus
from app.services.response_synthesizer import ResponseSynthesizer

logger = structlog.get_logger()


class Orchestrator:
    """
    Main orchestration layer that coordinates query processing.
    
    Flow:
    1. Classify intent using IntentClassifier
    2. Create execution plan using QueryPlanner
    3. Execute steps (parallel where possible)
    4. Synthesize response using ResponseSynthesizer
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.logger = logger.bind(component="orchestrator")
        
        from app.services.search_service import SearchService
        
        # Initialize components
        self.intent_classifier = IntentClassifier()
        self.query_planner = QueryPlanner()
        self.response_synthesizer = ResponseSynthesizer()
        self.search_service = SearchService(self.db)
        
        # User ID (mock for now)
        self.user_id = "00000000-0000-0000-0000-000000000001"
        
        # Initialize agents
        self.agents = {
            "gmail": GmailAgent(self.user_id, self.search_service),
            "gcal": GCalAgent(self.user_id, self.search_service),
            "gdrive": DriveAgent(self.user_id, self.search_service),
        }
    
    async def process(
        self,
        query: str,
        conversation_id: UUID,
        context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query.
        
        Args:
            query: User's natural language query
            conversation_id: Conversation ID for context tracking
            context: Previous queries for context
            
        Returns:
            Dict with response, intent, actions_taken
        """
        start_time = datetime.now()
        self.logger.info("Processing query", query=query, conversation_id=str(conversation_id))
        
        try:
            # Step 1: Classify intent
            intent = await self.intent_classifier.classify(query, context)
            self.logger.info("Intent classified", intent=intent.get("intent"))
            
            # Check for ambiguity
            if intent.get("ambiguous"):
                return {
                    "response": intent.get("clarification_needed", "Could you please clarify your request?"),
                    "intent": intent,
                    "actions_taken": [],
                }
            
            # Step 2: Create execution plan
            plan = await self.query_planner.create_plan(query, intent)
            self.logger.info("Plan created", num_steps=len(plan.steps))
            
            # Step 3: Execute plan
            results, actions_taken = await self._execute_plan(plan)
            
            # Step 4: Synthesize response
            self.logger.debug("Synthesizing response", num_results=len(results))
            response = await self.response_synthesizer.synthesize(
                query=query,
                intent=intent,
                results=results,
                actions_taken=actions_taken,
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.info(
                "Query processed successfully",
                execution_time=execution_time,
                results_count=sum(len(r.get("data", [])) for r in results),
            )
            
            return {
                "response": response,
                "intent": intent,
                "actions_taken": actions_taken,
                "execution_plan": {
                    "steps": [
                        {
                            "id": s.id,
                            "service": s.service,
                            "operation": s.operation,
                            "description": f"{s.operation.replace('_', ' ').title()} in {s.service}",
                            "status": s.status.value,
                            "depends_on": s.depends_on
                        }
                        for s in plan.steps
                    ],
                    "parallel_groups": plan.parallel_groups
                }
            }
            
        except Exception as e:
            self.logger.error("Query processing failed", error=str(e))
            return {
                "response": f"I encountered an error processing your request: {str(e)}",
                "intent": None,
                "actions_taken": [],
            }
    
    async def _execute_plan(
        self,
        plan: ExecutionPlan
    ) -> tuple[List[Dict], List[Dict]]:
        """
        Execute an execution plan, handling parallelism and dependencies.
        
        Returns:
            Tuple of (results, actions_taken)
        """
        results = []
        actions_taken = []
        completed_steps = set()
        step_results = {}  # Store results for dependent steps
        
        # Execute group by group (respecting dependencies)
        for group in plan.parallel_groups:
            # Get the actual step objects
            group_steps = [
                step for step in plan.steps
                if step.id in group
            ]
            
            # Execute all steps in the group in parallel
            tasks = [
                self._execute_step(step, step_results)
                for step in group_steps
            ]
            
            group_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for step, result in zip(group_steps, group_results):
                if isinstance(result, Exception):
                    plan.mark_failed(step.id, str(result))
                    self.logger.error("Step failed", step_id=step.id, error=str(result))
                else:
                    plan.mark_completed(step.id, result)
                    completed_steps.add(step.id)
                    step_results[step.id] = result
                    
                    # Categorize result
                    if step.operation == "search":
                        results.append({
                            "service": step.service,
                            "operation": step.operation,
                            "data": result,
                        })
                    else:
                        actions_taken.append({
                            "service": step.service,
                            "operation": step.operation,
                            "status": "success" if result else "failed",
                            "details": str(result) if result else None,
                        })
        
        return results, actions_taken
    
    async def _execute_step(
        self,
        step,
        previous_results: Dict
    ) -> Any:
        """Execute a single step"""
        agent = self.agents.get(step.service)
        if not agent:
            raise ValueError(f"Unknown service: {step.service}")
        
        self.logger.debug(
            "Executing step",
            step_id=step.id,
            service=step.service,
            operation=step.operation,
        )
        
        # Enrich params with results from dependencies
        params = step.params.copy()
        for dep_id in step.depends_on:
            if dep_id in previous_results:
                params[f"{dep_id}_result"] = previous_results[dep_id]
        
        # Execute based on operation type
        if step.operation == "search":
            results = await agent.search(
                query=params.get("query", ""),
                filters=params.get("filters"),
                limit=params.get("limit", 10),
            )
            # Convert SearchResult objects to dicts
            return [
                {
                    "id": r.id,
                    "title": r.title,
                    "preview": r.preview,
                    "metadata": r.metadata,
                    "relevance_score": r.relevance_score,
                }
                for r in results
            ]
        else:
            # Write operation (send, draft, create, etc.)
            result = await agent.execute(step.operation, params)
            return result.data if result.success else None
