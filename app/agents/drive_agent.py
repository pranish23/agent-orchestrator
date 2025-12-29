"""
Mock Google Drive Agent for development and testing
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from app.agents.base import BaseAgent, SearchResult, OperationResult


# Mock drive files
MOCK_FILES = [
    {
        "id": "file-001",
        "name": "Q4 Budget Report.pdf",
        "mime_type": "application/pdf",
        "parent_id": "folder-001",
        "content_preview": "Q4 2024 Budget Report\n\nRevenue: $2.5M\nExpenses: $1.8M\nNet: $700K\n\nKey highlights:\n- Marketing spend up 15%\n- New hires: 12\n- Project costs on budget",
        "shared_with": ["sarah@company.com", "cfo@company.com"],
        "modified_at": datetime.now() - timedelta(days=5),
        "size_bytes": 245000,
    },
    {
        "id": "file-002",
        "name": "Acme Corp Partnership Proposal.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "parent_id": "folder-002",
        "content_preview": "Partnership Proposal - Acme Corp\n\nExecutive Summary:\nProposed collaboration on Widget X development.\n\nTerms:\n- Revenue share: 60/40\n- Duration: 2 years\n- Investment: $500K",
        "shared_with": ["john.smith@acmecorp.com"],
        "modified_at": datetime.now() - timedelta(days=3),
        "size_bytes": 89000,
    },
    {
        "id": "file-003",
        "name": "2024 Roadmap.xlsx",
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "parent_id": "folder-001",
        "content_preview": "2024 Product Roadmap\n\nQ1: Feature A, Feature B\nQ2: Integration C\nQ3: Scale infrastructure\nQ4: Enterprise features",
        "shared_with": ["team@company.com"],
        "modified_at": datetime.now() - timedelta(days=30),
        "size_bytes": 156000,
    },
    {
        "id": "file-004",
        "name": "Meeting Notes - Client Calls.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "parent_id": "folder-002",
        "content_preview": "Client Meeting Notes\n\nAcme Corp - Jan 10:\n- Discussed partnership terms\n- Follow up on Widget X specs\n\nGlobex - Jan 12:\n- Renewal negotiation\n- Upsell opportunity",
        "shared_with": [],
        "modified_at": datetime.now() - timedelta(days=2),
        "size_bytes": 45000,
    },
    {
        "id": "file-005",
        "name": "Out of Office Schedule.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "parent_id": "root",
        "content_preview": "Out of Office Schedule\n\nJan 15-19: Company offsite\nFeb 5-7: Personal time\nMar 20-25: Conference travel\n\nBackup: Sarah (sarah@company.com)",
        "shared_with": ["manager@company.com"],
        "modified_at": datetime.now() - timedelta(days=10),
        "size_bytes": 23000,
    },
    {
        "id": "file-006",
        "name": "Project Timeline.pdf",
        "mime_type": "application/pdf",
        "parent_id": "folder-003",
        "content_preview": "Project Widget X Timeline\n\nPhase 1: Design (Jan-Feb)\nPhase 2: Development (Mar-May)\nPhase 3: Testing (Jun)\nPhase 4: Launch (Jul)",
        "shared_with": ["team@company.com", "john.smith@acmecorp.com"],
        "modified_at": datetime.now() - timedelta(days=15),
        "size_bytes": 178000,
    },
    {
        "id": "file-007",
        "name": "Invoice Template.xlsx",
        "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "parent_id": "folder-004",
        "content_preview": "Invoice Template\n\nCompany: [Your Company]\nClient: [Client Name]\nAmount: [Amount]\nDue Date: [Date]",
        "shared_with": [],
        "modified_at": datetime.now() - timedelta(days=60),
        "size_bytes": 34000,
    },
]

MOCK_FOLDERS = [
    {"id": "folder-001", "name": "Finance", "parent_id": "root"},
    {"id": "folder-002", "name": "Clients", "parent_id": "root"},
    {"id": "folder-003", "name": "Projects", "parent_id": "root"},
    {"id": "folder-004", "name": "Templates", "parent_id": "root"},
]


class DriveAgent(BaseAgent):
    """
    Mock Google Drive agent for development.
    
    Implements file search, reading, sharing, and organization.
    Uses in-memory mock data instead of actual Drive API.
    """
    
    def __init__(self, user_id: str, search_service: Optional[Any] = None):
        super().__init__(user_id)
        self.service_name = "gdrive"
        self.search_service = search_service
        self._files = MOCK_FILES.copy()
        self._folders = MOCK_FOLDERS.copy()
    
    async def search(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[SearchResult]:
        """
        Search Drive files by name, content, type, etc.
        """
        self._log_operation("search_files", query=query, filters=filters)
        
        # Use SearchService if available
        if self.search_service:
            try:
                hits = await self.search_service.search(
                    query=query,
                    user_id=self.user_id,
                    services=["gdrive"],
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
        
        for file in self._files:
            match_score = 0
            
            # Keyword matching
            for word in query_words:
                if word in file["name"].lower() or (file.get("content_preview") and word in file["content_preview"].lower()):
                    match_score += 0.2
            
            if query_lower and query_lower in file["name"].lower():
                match_score += 0.5
            
            # Filter by MIME type
            if filters.get("mime_type"):
                if filters["mime_type"] not in file["mime_type"]:
                    continue
            
            # Filter by file extension/type
            if filters.get("file_type"):
                file_type = filters["file_type"].lower()
                if file_type == "pdf" and "pdf" not in file["mime_type"]:
                    continue
                elif file_type == "doc" and "document" not in file["mime_type"]:
                    continue
                elif file_type == "sheet" and "spreadsheet" not in file["mime_type"]:
                    continue
            
            # Filter by modified date
            if filters.get("modified_after"):
                if file["modified_at"] < filters["modified_after"]:
                    continue
            
            if match_score > 0 or not query_words:
                results.append(SearchResult(
                    id=file["id"],
                    title=file["name"],
                    preview=file.get("content_preview", "")[:200] + "...",
                    metadata={
                        "mime_type": file["mime_type"],
                        "modified_at": file["modified_at"].isoformat(),
                        "size_bytes": file["size_bytes"],
                        "shared_with": file["shared_with"],
                    },
                    relevance_score=max(match_score, 0.1),
                ))
        
        # Sort by relevance, then by modified date
        results.sort(key=lambda x: (-x.relevance_score, x.metadata["modified_at"]))
        return results[:limit]
    
    async def execute(
        self,
        operation: str,
        params: Dict[str, Any]
    ) -> OperationResult:
        """
        Execute Drive operations: share, create_folder, move.
        """
        self._log_operation(operation, params=params)
        
        if operation == "share_file":
            return await self._share_file(params)
        elif operation == "create_folder":
            return await self._create_folder(params)
        elif operation == "move_file":
            return await self._move_file(params)
        elif operation == "create_file":
            return await self._create_file(params)
        else:
            return OperationResult(
                success=False,
                operation=operation,
                error=f"Unknown operation: {operation}"
            )
    
    async def _create_file(self, params: Dict[str, Any]) -> OperationResult:
        """Create a new file"""
        name = params.get("name")
        if not name:
            return OperationResult(
                success=False,
                operation="create_file",
                error="Missing file name"
            )
            
        file_id = f"file-{uuid4().hex[:8]}"
        mime_type = params.get("mime_type", "application/vnd.google-apps.document")
        
        # Determine extension if missing
        if "." not in name:
            if "spreadsheet" in mime_type or "sheet" in mime_type:
                name += ".xlsx"
            else:
                name += ".docx"

        new_file = {
            "id": file_id,
            "name": name,
            "mime_type": mime_type,
            "parent_id": params.get("parent_id", "root"),
            "content_preview": params.get("content", "Empty document"),
            "shared_with": [],
            "modified_at": datetime.now(),
            "size_bytes": len(params.get("content", ""))
        }
        self._files.append(new_file)
        
        return OperationResult(
            success=True,
            operation="create_file",
            data={
                "file_id": file_id,
                "name": name,
                "message": f"File '{name}' created successfully",
            }
        )
    
    async def _share_file(self, params: Dict[str, Any]) -> OperationResult:
        """Share a file with someone"""
        file_id = params.get("file_id")
        email = params.get("email")
        
        if not file_id or not email:
            return OperationResult(
                success=False,
                operation="share_file",
                error="Missing file_id or email"
            )
        
        for file in self._files:
            if file["id"] == file_id:
                if email not in file["shared_with"]:
                    file["shared_with"].append(email)
                return OperationResult(
                    success=True,
                    operation="share_file",
                    data={
                        "file_id": file_id,
                        "shared_with": email,
                        "permission": params.get("permission", "view"),
                        "message": f"File shared with {email}",
                    }
                )
        
        return OperationResult(
            success=False,
            operation="share_file",
            error=f"File not found: {file_id}"
        )
    
    async def _create_folder(self, params: Dict[str, Any]) -> OperationResult:
        """Create a new folder"""
        name = params.get("name")
        if not name:
            return OperationResult(
                success=False,
                operation="create_folder",
                error="Missing folder name"
            )
        
        folder_id = f"folder-{uuid4().hex[:8]}"
        new_folder = {
            "id": folder_id,
            "name": name,
            "parent_id": params.get("parent_id", "root"),
        }
        self._folders.append(new_folder)
        
        return OperationResult(
            success=True,
            operation="create_folder",
            data={
                "folder_id": folder_id,
                "name": name,
                "message": "Folder created successfully",
            }
        )
    
    async def _move_file(self, params: Dict[str, Any]) -> OperationResult:
        """Move a file to a different folder"""
        file_id = params.get("file_id")
        destination_id = params.get("destination_id")
        
        if not file_id or not destination_id:
            return OperationResult(
                success=False,
                operation="move_file",
                error="Missing file_id or destination_id"
            )
        
        for file in self._files:
            if file["id"] == file_id:
                file["parent_id"] = destination_id
                return OperationResult(
                    success=True,
                    operation="move_file",
                    data={
                        "file_id": file_id,
                        "destination_id": destination_id,
                        "message": "File moved successfully",
                    }
                )
        
        return OperationResult(
            success=False,
            operation="move_file",
            error=f"File not found: {file_id}"
        )
    
    async def get_context(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get full file details and content preview"""
        for file in self._files:
            if file["id"] == item_id:
                return {
                    **file,
                    "modified_at": file["modified_at"].isoformat(),
                }
        return None
    
    async def search_pdfs(self, query: str = "", limit: int = 10) -> List[SearchResult]:
        """Search specifically for PDF files"""
        return await self.search(query, filters={"file_type": "pdf"}, limit=limit)
    
    async def get_recent_files(self, days: int = 30, limit: int = 10) -> List[SearchResult]:
        """Get recently modified files"""
        modified_after = datetime.now() - timedelta(days=days)
        return await self.search("", filters={"modified_after": modified_after}, limit=limit)
