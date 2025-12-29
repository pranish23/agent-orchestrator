"""
Tool Registry - Defines available agent capabilities (MCP-style)
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Parameter definition for a tool"""
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[List[str]] = None


class ToolDefinition(BaseModel):
    """Standard definition of a tool capability"""
    name: str
    description: str
    parameters: List[ToolParameter]
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format / MCP schema"""
        properties = {}
        required = []
        
        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description
            }
            if param.enum:
                prop["enum"] = param.enum
            
            properties[param.name] = prop
            
            if param.required:
                required.append(param.name)
                
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }


class ToolRegistry:
    """Registry of all available agent tools"""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_default_tools()
        
    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        return self.tools.get(name)
        
    def get_all_tools(self) -> List[ToolDefinition]:
        return list(self.tools.values())
        
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        return [tool.to_json_schema() for tool in self.tools.values()]
        
    def _register_default_tools(self):
        """Register the core capabilities of the agents"""
        
        # ============ Gmail Tools ============
        self.tools["gmail_search"] = ToolDefinition(
            name="gmail_search",
            description="Search for emails using keywords, sender, or date.",
            parameters=[
                ToolParameter(name="query", type="string", description="Search query string (e.g., 'from:john', 'subject:meeting')"),
                ToolParameter(name="limit", type="integer", description="Max number of results", required=False),
            ]
        )
        
        self.tools["gmail_send_email"] = ToolDefinition(
            name="gmail_send_email",
            description="Send an email to one or more recipients.",
            parameters=[
                ToolParameter(name="to", type="array", description="List of recipient email addresses"),
                ToolParameter(name="subject", type="string", description="Email subject line"),
                ToolParameter(name="body", type="string", description="Email body content"),
            ]
        )
        
        self.tools["gmail_create_draft"] = ToolDefinition(
            name="gmail_create_draft",
            description="Create a draft email without sending it.",
            parameters=[
                ToolParameter(name="to", type="array", description="List of recipient email addresses"),
                ToolParameter(name="subject", type="string", description="Draft subject line"),
                ToolParameter(name="body", type="string", description="Draft body content"),
            ]
        )
        
        # ============ Calendar Tools ============
        self.tools["gcal_search_events"] = ToolDefinition(
            name="gcal_search_events",
            description="Search for calendar events by title, time, or attendees.",
            parameters=[
                ToolParameter(name="query", type="string", description="Search keywords"),
                ToolParameter(name="limit", type="integer", description="Max results", required=False),
            ]
        )
        
        self.tools["gcal_create_event"] = ToolDefinition(
            name="gcal_create_event",
            description="Schedule a new calendar event.",
            parameters=[
                ToolParameter(name="title", type="string", description="Event title"),
                ToolParameter(name="start_time", type="string", description="Start time (ISO 8601 string)"),
                ToolParameter(name="end_time", type="string", description="End time (ISO 8601 string)"),
                ToolParameter(name="attendees", type="array", description="List of attendee emails", required=False),
                ToolParameter(name="description", type="string", description="Event description", required=False),
            ]
        )
        
        # ============ Drive Tools ============
        self.tools["gdrive_search_files"] = ToolDefinition(
            name="gdrive_search_files",
            description="Search for documents and files in Google Drive.",
            parameters=[
                ToolParameter(name="query", type="string", description="Search keywords"),
                ToolParameter(name="limit", type="integer", description="Max results", required=False),
            ]
        )
        
        self.tools["gdrive_create_file"] = ToolDefinition(
            name="gdrive_create_file",
            description="Create a new file (doc, sheet, etc.) in Drive.",
            parameters=[
                ToolParameter(name="name", type="string", description="Name of the file"),
                ToolParameter(name="content", type="string", description="Initial content of the file", required=False),
                ToolParameter(name="mime_type", type="string", description="MIME type (default: google-apps.document)", required=False),
            ]
        )

        self.tools["gdrive_share_file"] = ToolDefinition(
            name="gdrive_share_file",
            description="Share a file with another user.",
            parameters=[
                ToolParameter(name="file_id", type="string", description="ID of the file to share"),
                ToolParameter(name="email", type="string", description="Email of the user to share with"),
                ToolParameter(name="role", type="string", description="Role: 'reader', 'commenter', 'writer'", required=False, enum=["reader", "commenter", "writer"]),
            ]
        )
