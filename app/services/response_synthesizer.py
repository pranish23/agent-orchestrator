"""
Response Synthesizer - Generates natural language from execution results
"""
from typing import Any, Dict, List, Optional
from datetime import datetime
import structlog
from app.config import settings
from app.services.llm_provider import get_llm_provider

logger = structlog.get_logger()


RESPONSE_SYNTHESIS_PROMPT = """You are an assistant synthesizing results from Google Workspace services.

Generate a clear, helpful response based on the query and results below.

User Query: {query}
Current Date: {current_date}

Intent: {intent}

Results:
{results}

Instructions:
1. Summarize the key findings concisely
2. Use bullet points for multiple items
3. Highlight important details (dates, times, senders)
4. If actions were taken (drafts, events created), confirm them
5. If results are empty, acknowledge and suggest alternatives
6. If clarification was needed, ask the question
7. End with a suggested next action if appropriate

Respond in a friendly, helpful tone. Use markdown formatting for readability.
"""


class ResponseSynthesizer:
    """
    Synthesizes natural language responses from execution results.
    
    Aggregates results from multiple services and generates
    contextual, helpful responses.
    """
    
    def __init__(self):
        self.provider = get_llm_provider(settings)
        self.logger = logger.bind(component="response_synthesizer")
    
    async def synthesize(
        self,
        query: str,
        intent: Dict[str, Any],
        results: List[Dict[str, Any]],
        actions_taken: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate a natural language response from results.
        
        Args:
            query: Original user query
            intent: Classified intent
            results: Results from service agents
            actions_taken: Any actions performed (drafts, creates, etc.)
            
        Returns:
            Natural language response string
        """
        
        # Check if clarification is needed
        if intent.get("ambiguous") and intent.get("clarification_needed"):
            return intent["clarification_needed"]
        
        # Try LLM synthesis first
        if self.provider:
            try:
                return await self._synthesize_with_llm(query, intent, results, actions_taken)
            except Exception as e:
                self.logger.warning("LLM synthesis failed, using template", error=str(e), exc_info=True)
        
        # Fallback to template-based synthesis
        return self._synthesize_with_templates(query, intent, results, actions_taken)
    
    async def _synthesize_with_llm(
        self,
        query: str,
        intent: Dict[str, Any],
        results: List[Dict[str, Any]],
        actions_taken: Optional[List[Dict]] = None
    ) -> str:
        """Use LLM provider to synthesize a response"""
        results_str = self._format_results_for_llm(results, actions_taken)
        
        prompt = RESPONSE_SYNTHESIS_PROMPT.format(
            query=query,
            intent=intent.get("intent", "general"),
            results=results_str,
            current_date=datetime.now().strftime("%A, %b %d, %Y")
        )
        
        input_tokens = len(prompt.split())  # Rough estimate
        max_output = 4096
        
        self.logger.debug("Calling LLM", input_tokens=input_tokens, max_output=max_output)
        
        response_text = await self.provider.chat_completion(
            prompt=prompt,
            temperature=0.7,
            max_tokens=max_output
        )
        
        return response_text.strip()
    
    def _synthesize_with_templates(
        self,
        query: str,
        intent: Dict[str, Any],
        results: List[Dict[str, Any]],
        actions_taken: Optional[List[Dict]] = None
    ) -> str:
        """Template-based response synthesis"""
        self.logger.debug("Synthesizing with templates", services=[r.get("service") for r in results])
        intent_type = intent.get("intent", "general_search")
        
        # Route to appropriate template
        if intent_type == "cancel_flight":
            return self._format_cancel_flight(results, actions_taken)
        elif intent_type == "prepare_meeting":
            return self._format_prepare_meeting(results, actions_taken)
        elif intent_type == "search_emails":
            return self._format_email_search(results)
        elif intent_type == "search_events":
            return self._format_event_search(results)
        elif intent_type == "search_files":
            return self._format_file_search(results)
        else:
            return self._format_general_search(results)
    
    def _format_results_for_llm(
        self,
        results: List[Dict],
        actions_taken: Optional[List[Dict]] = None
    ) -> str:
        """Format results for LLM prompt"""
        lines = []
        
        for result in results:
            service = result.get("service", "unknown")
            data = result.get("data", [])
            
            lines.append(f"\n## {service.upper()} Results:")
            
            if not data:
                lines.append("No results found.")
            else:
                for item in data[:5]:  # Limit to prevent token overflow
                    lines.append(f"- {item.get('title', 'Untitled')}")
                    
                    # Add metadata context
                    metadata = item.get("metadata", {})
                    if service == "gmail":
                        if sender := metadata.get("sender"):
                            lines.append(f"  From: {sender}")
                        if date := metadata.get("received_at"):
                            lines.append(f"  Date: {date}")
                    elif service == "gcal":
                        if start := metadata.get("start_time"):
                            lines.append(f"  Time: {start}")
                        if location := item.get("location"):
                            lines.append(f"  Location: {location}")
                    elif service == "gdrive":
                        if mime := metadata.get("mime_type"):
                            lines.append(f"  Type: {mime}")
                        if modified := metadata.get("modified_at"):
                            lines.append(f"  Modified: {modified}")
                            
                    if item.get("preview"):
                        lines.append(f"  Preview: {item['preview'][:150]}...")
        
        if actions_taken:
            lines.append("\n## Actions Taken:")
            for action in actions_taken:
                lines.append(f"- {action.get('operation', 'Unknown')}: {action.get('status', 'unknown')}")
                if details := action.get("details"):
                    lines.append(f"  {details}")
        
        return "\n".join(lines)
    
    def _format_cancel_flight(
        self,
        results: List[Dict],
        actions_taken: Optional[List[Dict]] = None
    ) -> str:
        """Format cancel flight response"""
        response_parts = []
        
        # Find email and calendar results
        email_result = next((r for r in results if r.get("service") == "gmail"), None)
        cal_result = next((r for r in results if r.get("service") == "gcal"), None)
        
        if email_result and email_result.get("data"):
            email = email_result["data"][0]
            response_parts.append(f"✓ Found your booking confirmation: **{email.get('title', 'Booking')}**")
        
        if cal_result and cal_result.get("data"):
            event = cal_result["data"][0]
            response_parts.append(f"✓ Found calendar event: **{event.get('title', 'Flight')}**")
        
        # Check for draft action
        draft_action = next(
            (a for a in (actions_taken or []) if a.get("operation") == "draft_email"),
            None
        )
        if draft_action and draft_action.get("status") == "success":
            response_parts.append("✓ **Drafted cancellation email**")
            response_parts.append("\nWould you like me to send it?")
        
        if not response_parts:
            return "I couldn't find any flight booking information. Could you provide more details about the airline or booking reference?"
        
        return "\n".join(response_parts)
    
    def _format_prepare_meeting(
        self,
        results: List[Dict],
        actions_taken: Optional[List[Dict]] = None
    ) -> str:
        """Format meeting preparation response"""
        response_parts = ["Here's what I found for your meeting:\n"]
        
        # Calendar results
        cal_result = next((r for r in results if r.get("service") == "gcal"), None)
        if cal_result and cal_result.get("data"):
            event = cal_result["data"][0]
            response_parts.append(f"📅 **Meeting:** {event.get('title', 'Untitled')}")
            if preview := event.get("preview"):
                response_parts.append(f"   {preview}")
        
        # Email results
        email_result = next((r for r in results if r.get("service") == "gmail"), None)
        if email_result and email_result.get("data"):
            response_parts.append(f"\n📧 **Related Emails:** ({len(email_result['data'])} found)")
            for email in email_result["data"][:3]:
                response_parts.append(f"   - {email.get('title', 'Email')}")
        
        # Drive results
        drive_result = next((r for r in results if r.get("service") == "gdrive"), None)
        if drive_result and drive_result.get("data"):
            response_parts.append(f"\n📁 **Related Documents:** ({len(drive_result['data'])} found)")
            for file in drive_result["data"][:3]:
                response_parts.append(f"   - {file.get('title', 'Document')}")
        
        return "\n".join(response_parts)
    
    def _format_email_search(self, results: List[Dict]) -> str:
        """Format email search results"""
        email_result = next((r for r in results if r.get("service") == "gmail"), None)
        
        if not email_result or not email_result.get("data"):
            return "I couldn't find any matching emails."
        
        emails = email_result["data"]
        response_parts = [f"Found **{len(emails)}** matching email(s):\n"]
        
        for email in emails[:5]:
            sender = email.get("metadata", {}).get("sender", "Unknown")
            response_parts.append(f"📧 **{email.get('title', 'Untitled')}**")
            response_parts.append(f"   From: {sender}")
            if preview := email.get("preview"):
                response_parts.append(f"   _{preview[:80]}..._\n")
        
        return "\n".join(response_parts)
    
    def _format_event_search(self, results: List[Dict]) -> str:
        """Format calendar event search results"""
        cal_result = next((r for r in results if r.get("service") == "gcal"), None)
        
        if not cal_result or not cal_result.get("data"):
            return "No calendar events found matching your query."
        
        events = cal_result["data"]
        response_parts = [f"Found **{len(events)}** event(s):\n"]
        
        for event in events[:10]:
            response_parts.append(f"📅 **{event.get('title', 'Untitled')}**")
            response_parts.append(f"   {event.get('preview', '')}\n")
        
        return "\n".join(response_parts)
    
    def _format_file_search(self, results: List[Dict]) -> str:
        """Format Drive file search results"""
        drive_result = next((r for r in results if r.get("service") == "gdrive"), None)
        
        if not drive_result or not drive_result.get("data"):
            return "No files found in Drive matching your query."
        
        files = drive_result["data"]
        response_parts = [f"Found **{len(files)}** file(s):\n"]
        
        for file in files[:10]:
            mime = file.get("metadata", {}).get("mime_type", "")
            icon = "📄" if "document" in mime else "📊" if "spreadsheet" in mime else "📁"
            response_parts.append(f"{icon} **{file.get('title', 'Untitled')}**")
            if preview := file.get("preview"):
                response_parts.append(f"   _{preview[:60]}..._\n")
        
        return "\n".join(response_parts)
    
    def _format_general_search(self, results: List[Dict]) -> str:
        """Format general search results across services"""
        response_parts = ["Here's what I found:\n"]
        
        has_results = False
        for result in results:
            service = result.get("service", "unknown")
            data = result.get("data", [])
            
            if data:
                has_results = True
                icon = {"gmail": "📧", "gcal": "📅", "gdrive": "📁"}.get(service, "📌")
                response_parts.append(f"\n{icon} **{service.upper()}:** ({len(data)} items)")
                for item in data[:3]:
                    response_parts.append(f"   - {item.get('title', 'Untitled')}")
        
        if not has_results:
            return "I couldn't find any results for your query. Could you try rephrasing or being more specific?"
        
        return "\n".join(response_parts)
