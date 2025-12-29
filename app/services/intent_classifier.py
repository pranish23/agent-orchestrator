"""
Intent Classifier - Parses natural language queries into structured intents
"""
from typing import Any, Dict, List, Optional
import json
import hashlib
import structlog
from app.config import settings
from app.services.llm_provider import get_llm_provider

logger = structlog.get_logger()


# Intent classification prompt
INTENT_CLASSIFICATION_PROMPT = """You are an intent classifier for a Google Workspace assistant.
Analyze the user's query and extract:
1. Which services are needed (gmail, gcal, gdrive)
2. The primary intent
3. Key entities (names, dates, subjects, etc.)
4. Required execution steps

Respond with valid JSON only, no explanation.

User Query: {query}

Conversation context (last queries):
{context}

JSON Response format:
{{
    "services": ["gmail", "gcal", "gdrive"],
    "intent": "intent_name",
    "entities": {{
        "time_reference": "tomorrow/next week/etc.",
        "email_addresses": ["user@example.com"],
        "company": "Company Name",
        "airline": "Airline Name (for flight intents)"
    }},
    "steps": ["step1", "step2"],
    "confidence": 0.95,
    "ambiguous": false,
    "clarification_needed": null
}}

Common intents:
- search_emails: Find specific emails (Service: gmail)
- search_events: Find calendar events (Service: gcal)
- search_files: Find Drive files (Service: gdrive)
- cancel_flight: Cancel a flight booking. REQUIRES checking BOTH Gmail (for booking) and GCal (for the event). (Services: gmail, gcal)
- prepare_meeting: Gather info for a meeting. REQUIRES checking Gmail, GCal, and GDrive. (Services: gmail, gcal, gdrive)
- schedule_event: Create calendar event (Service: gcal)
- draft_email: Draft an email (Service: gmail)
- send_email: Send an email (Service: gmail)
- share_file: Share a Drive file (Service: gdrive)

GUIDELINES:
- If the user mentions "flight" and "cancel", ALWAYS include BOTH "gmail" and "gcal" in services, and extract the airline into the "airline" entity.
- If the user mentions "prepare" and "meeting", ALWAYS include "gmail", "gcal", and "gdrive".
- Respond with valid JSON only.
"""


# Fallback patterns for when LLM is not available
FALLBACK_PATTERNS = {
    "calendar": {
        "keywords": ["calendar", "meeting", "event", "schedule", "appointment", "next week", "tomorrow"],
        "service": "gcal",
        "intent": "search_events",
    },
    "email": {
        "keywords": ["email", "mail", "message", "inbox", "send", "draft"],
        "service": "gmail",
        "intent": "search_emails",
    },
    "drive": {
        "keywords": ["file", "document", "pdf", "drive", "folder", "doc", "sheet"],
        "service": "gdrive",
        "intent": "search_files",
    },
    "flight": {
        "keywords": ["flight", "airline", "booking", "cancel"],
        "services": ["gmail", "gcal"],
        "intent": "cancel_flight",
    },
    "meeting_prep": {
        "keywords": ["prepare", "preparation", "ready for"],
        "services": ["gmail", "gcal", "gdrive"],
        "intent": "prepare_meeting",
    },
}


class IntentClassifier:
    """
    Classifies natural language queries into structured intents.
    
    Uses OpenAI/Anthropic for classification with fallback to
    pattern matching when API is unavailable.
    """
    
    def __init__(self):
        self.provider = get_llm_provider(settings)
        self.logger = logger.bind(component="intent_classifier")
        self._cache: Dict[str, Dict] = {}  # Simple in-memory cache
    
    async def classify(
        self,
        query: str,
        context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Classify a query into a structured intent.
        
        Args:
            query: The natural language query
            context: Previous queries for conversation context
            
        Returns:
            Structured intent with services, intent type, entities, and steps
        """
        if not query:
            return {
                "services": ["gmail", "gcal", "gdrive"],
                "intent": "general_search",
                "entities": {},
                "steps": [],
                "confidence": 0.0,
                "ambiguous": False,
                "clarification_needed": None
            }
            
        # Check cache first
        cache_key = self._get_cache_key(query, context)
        if cache_key in self._cache:
            self.logger.debug("Intent cache hit", query=query[:50])
            return self._cache[cache_key]
        
        # Try LLM classification first
        if self.provider:
            try:
                result = await self._classify_with_llm(query, context)
                self._cache[cache_key] = result
                return result
            except Exception as e:
                self.logger.warning("LLM classification failed, using fallback", error=str(e), exc_info=True)
        
        # Fallback to pattern matching
        result = self._classify_with_patterns(query)
        self._cache[cache_key] = result
        return result
    
    async def _classify_with_llm(
        self,
        query: str,
        context: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Use LLM provider to classify the intent"""
        context_str = "\n".join(context[-5:]) if context else "No previous context"
        
        prompt = INTENT_CLASSIFICATION_PROMPT.format(
            query=query,
            context=context_str,
        )
        
        response_text = await self.provider.chat_completion(
            prompt=prompt,
            response_format="json",
            temperature=0.1,
            max_tokens=2048
        )
        
        # Clean potential markdown code blocks
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
        
        result = json.loads(clean_text.strip())
        
        # Sanitize LLM response to prevent validation errors
        if not result.get("intent"):
            self.logger.warning("LLM returned empty intent, defaulting to general_search")
            result["intent"] = "general_search"
            
        if result.get("services") is None:
            result["services"] = ["gmail", "gcal", "gdrive"]
            
        if result.get("entities") is None:
            result["entities"] = {}
            
        if result.get("steps") is None:
            # Generate default steps if missing
            intent_type = result["intent"]
            services = result["services"]
            result["steps"] = self._generate_steps(intent_type, services)
        
        self.logger.info(
            "Intent classified via LLM",
            intent=result.get("intent"),
            services=result.get("services"),
            confidence=result.get("confidence"),
        )
        
        return result
    
    def _classify_with_patterns(self, query: str) -> Dict[str, Any]:
        """Fallback pattern-based classification"""
        query_lower = query.lower()
        
        matched_services = set()
        matched_intent = "general_search"
        matched_confidence = 0.5
        
        # Check each pattern
        for pattern_name, pattern in FALLBACK_PATTERNS.items():
            matching_keywords = [kw for kw in pattern["keywords"] if kw in query_lower]
            if matching_keywords:
                if "services" in pattern:
                    matched_services.update(pattern["services"])
                else:
                    matched_services.add(pattern["service"])
                matched_intent = pattern["intent"]
                matched_confidence = min(0.3 + len(matching_keywords) * 0.1, 0.8)
        
        # Default to all services if none matched
        if not matched_services:
            matched_services = {"gmail", "gcal", "gdrive"}
            matched_intent = "general_search"
            matched_confidence = 0.3
        
        # Extract basic entities
        entities = self._extract_basic_entities(query)
        
        # Generate steps based on intent
        steps = self._generate_steps(matched_intent, list(matched_services))
        
        result = {
            "services": list(matched_services),
            "intent": matched_intent,
            "entities": entities,
            "steps": steps,
            "confidence": matched_confidence,
            "ambiguous": False,
            "clarification_needed": None,
        }
        
        self.logger.info(
            "Intent classified via patterns",
            intent=matched_intent,
            services=list(matched_services),
            confidence=matched_confidence,
        )
        
        return result
    
    def _extract_basic_entities(self, query: str) -> Dict[str, Any]:
        """Extract basic entities from query using patterns"""
        entities = {}
        
        # Extract email addresses
        import re
        emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', query)
        if emails:
            entities["email_addresses"] = emails
        
        # Extract common time references
        time_refs = ["tomorrow", "next week", "this week", "today", "yesterday", "last week", "next month"]
        for ref in time_refs:
            if ref in query.lower():
                entities["time_reference"] = ref
                break
        
        # Extract airline names (for flight queries)
        airlines = ["turkish airlines", "emirates", "lufthansa", "united", "delta", "american"]
        for airline in airlines:
            if airline in query.lower():
                entities["airline"] = airline.title()
                break
        
        # Extract company names (common pattern: "with X Corp/Company")
        company_match = re.search(r'with\s+(\w+(?:\s+\w+)?)\s*(?:corp|company|inc)?', query, re.IGNORECASE)
        if company_match:
            entities["company"] = company_match.group(1)
        
        return entities
    
    def _generate_steps(self, intent: str, services: List[str]) -> List[str]:
        """Generate execution steps based on intent"""
        step_templates = {
            "cancel_flight": [
                "search_gmail_for_booking",
                "find_calendar_event",
                "draft_cancellation_email",
            ],
            "prepare_meeting": [
                "find_calendar_event",
                "search_related_emails",
                "search_related_documents",
            ],
            "search_emails": ["search_emails"],
            "search_events": ["search_events"],
            "search_files": ["search_files"],
            "draft_email": ["draft_email"],
            "send_email": ["compose_email", "send_email"],
            "share_file": ["find_file", "share_file"],
            "general_search": [f"search_{svc}" for svc in services],
        }
        
        return step_templates.get(intent, ["search"])
    
    def _get_cache_key(self, query: str, context: Optional[List[str]]) -> str:
        """Generate cache key for query"""
        context_str = "|".join(context[-3:]) if context else ""
        content = f"{query}|{context_str}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def clear_cache(self):
        """Clear the intent cache"""
        self._cache.clear()
