"""
Search Service - Hybrid vector + keyword search
"""
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, and_, or_
from sqlalchemy.dialects.postgresql import insert

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.models import GmailCache, GCalCache, GDriveCache

logger = structlog.get_logger()


@dataclass
class SearchHit:
    """A search result with relevance scoring"""
    id: str
    service: str
    title: str
    preview: str
    metadata: Dict[str, Any]
    vector_score: float  # Cosine similarity score
    keyword_score: float  # Keyword match score
    recency_score: float  # Recency boost
    final_score: float  # Combined score
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "service": self.service,
            "title": self.title,
            "preview": self.preview,
            "metadata": self.metadata,
            "relevance_score": self.final_score,
        }


class SearchService:
    """
    Hybrid search service combining vector similarity and keyword filtering.
    
    Features:
    - Vector similarity search using pgvector
    - Metadata filtering (date, sender, type)
    - Recency boosting
    - Score fusion for ranking
    """
    
    def __init__(self, db: AsyncSession, redis_client=None):
        self.db = db
        self.redis = redis_client
        self.embedding_service = EmbeddingService(redis_client)
        self.logger = logger.bind(component="search_service")
        
        # Search configuration
        self.vector_weight = 0.6
        self.keyword_weight = 0.3
        self.recency_weight = 0.1
    
    async def search(
        self,
        query: str,
        user_id: str,
        services: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10
    ) -> List[SearchHit]:
        """
        Perform hybrid search across services.
        
        Args:
            query: Search query
            user_id: User ID
            services: Services to search (gmail, gcal, gdrive)
            filters: Optional filters (date_range, sender, file_type)
            limit: Max results per service
            
        Returns:
            List of SearchHit objects sorted by relevance
        """
        services = services or ["gmail", "gcal", "gdrive"]
        filters = filters or {}
        
        self.logger.info(
            "Performing hybrid search",
            query=query[:50],
            services=services,
            filters=list(filters.keys()),
        )
        
        # Generate query embedding
        query_embedding = await self.embedding_service.generate_embedding(query)
        if not query_embedding:
            self.logger.warning("Failed to generate query embedding")
            return []
        
        # Search each service
        all_results = []
        for service in services:
            results = await self._search_service(
                service=service,
                query=query,
                query_embedding=query_embedding,
                user_id=user_id,
                filters=filters,
                limit=limit,
            )
            all_results.extend(results)
        
        # Sort by final score
        all_results.sort(key=lambda x: x.final_score, reverse=True)
        
        return all_results[:limit]
    
    async def _search_service(
        self,
        service: str,
        query: str,
        query_embedding: List[float],
        user_id: str,
        filters: Dict[str, Any],
        limit: int
    ) -> List[SearchHit]:
        """Search a specific service"""
        
        # Get model class
        model_map = {
            "gmail": GmailCache,
            "gcal": GCalCache,
            "gdrive": GDriveCache,
        }
        model = model_map.get(service)
        if not model:
            return []
        
        # Build vector search query
        # Using pgvector's cosine distance: 1 - cosine_distance
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        try:
            # Use raw SQL for pgvector operations
            sql = self._build_search_query(service, embedding_str, user_id, filters, limit)
            result = await self.db.execute(text(sql))
            rows = result.fetchall()
            
            # Convert to SearchHit objects
            hits = []
            for row in rows:
                hit = self._row_to_search_hit(service, row, query)
                if hit:
                    hits.append(hit)
            
            return hits
            
        except Exception as e:
            self.logger.error("Search query failed", service=service, error=str(e))
            return []
    
    def _build_search_query(
        self,
        service: str,
        embedding_str: str,
        user_id: str,
        filters: Dict[str, Any],
        limit: int
    ) -> str:
        """Build the SQL query for pgvector search"""
        
        table_name = f"{service}_cache"
        
        # Base columns
        if service == "gmail":
            select_cols = "id, email_id, subject, sender, body_preview, received_at"
            order_col = "received_at"
        elif service == "gcal":
            select_cols = "id, event_id, title, description, location, start_time, end_time"
            order_col = "start_time"
        else:  # gdrive
            select_cols = "id, file_id, name, mime_type, content_preview, modified_at"
            order_col = "modified_at"
        
        # Vector similarity score
        vector_score = f"1 - (embedding <=> '{embedding_str}'::vector) as vector_score"
        
        # Build WHERE clause
        where_clauses = [f"user_id = '{user_id}'"]
        
        if filters.get("sender") and service == "gmail":
            where_clauses.append(f"sender ILIKE '%{filters['sender']}%'")
        
        if filters.get("attendee") and service == "gcal":
            where_clauses.append(f"attendees::text ILIKE '%{filters['attendee']}%'")
        
        if filters.get("file_type") and service == "gdrive":
            mime_patterns = {
                "pdf": "application/pdf",
                "doc": "document",
                "sheet": "spreadsheet",
            }
            pattern = mime_patterns.get(filters["file_type"].lower(), filters["file_type"])
            where_clauses.append(f"mime_type ILIKE '%{pattern}%'")
        
        if filters.get("from_date"):
            where_clauses.append(f"{order_col} >= '{filters['from_date']}'")
        
        if filters.get("to_date"):
            where_clauses.append(f"{order_col} <= '{filters['to_date']}'")
        
        where_clause = " AND ".join(where_clauses)
        
        # Final query
        sql = f"""
        SELECT 
            {select_cols},
            {vector_score}
        FROM {table_name}
        WHERE {where_clause}
            AND embedding IS NOT NULL
        ORDER BY embedding <=> '{embedding_str}'::vector
        LIMIT {limit}
        """
        
        return sql
    
    def _row_to_search_hit(self, service: str, row, query: str) -> Optional[SearchHit]:
        """Convert database row to SearchHit"""
        try:
            # Calculate keyword score
            keyword_score = self._calculate_keyword_score(row, query)
            
            # Calculate recency score
            recency_score = self._calculate_recency_score(row, service)
            
            # Get vector score from row
            vector_score = float(row[-1])  # Last column is vector_score
            
            # Calculate final score
            final_score = (
                self.vector_weight * vector_score +
                self.keyword_weight * keyword_score +
                self.recency_weight * recency_score
            )
            
            # Extract fields based on service
            if service == "gmail":
                return SearchHit(
                    id=str(row[1]),  # email_id
                    service=service,
                    title=row[2] or "No Subject",  # subject
                    preview=row[4][:200] if row[4] else "",  # body_preview
                    metadata={
                        "sender": row[3],
                        "received_at": row[5].isoformat() if row[5] else None,
                    },
                    vector_score=vector_score,
                    keyword_score=keyword_score,
                    recency_score=recency_score,
                    final_score=final_score,
                )
            elif service == "gcal":
                return SearchHit(
                    id=str(row[1]),  # event_id
                    service=service,
                    title=row[2] or "Untitled Event",  # title
                    preview=f"{row[4] or ''}"[:200],  # location
                    metadata={
                        "description": row[3],
                        "start_time": row[5].isoformat() if row[5] else None,
                        "end_time": row[6].isoformat() if row[6] else None,
                    },
                    vector_score=vector_score,
                    keyword_score=keyword_score,
                    recency_score=recency_score,
                    final_score=final_score,
                )
            else:  # gdrive
                return SearchHit(
                    id=str(row[1]),  # file_id
                    service=service,
                    title=row[2] or "Untitled",  # name
                    preview=row[4][:200] if row[4] else "",  # content_preview
                    metadata={
                        "mime_type": row[3],
                        "modified_at": row[5].isoformat() if row[5] else None,
                    },
                    vector_score=vector_score,
                    keyword_score=keyword_score,
                    recency_score=recency_score,
                    final_score=final_score,
                )
        except Exception as e:
            self.logger.debug("Failed to convert row", error=str(e))
            return None
    
    def _calculate_keyword_score(self, row, query: str) -> float:
        """Calculate keyword match score"""
        query_lower = query.lower()
        query_terms = query_lower.split()
        
        # Convert row to text for matching
        text = " ".join(str(col).lower() for col in row if col)
        
        # Count matching terms
        matches = sum(1 for term in query_terms if term in text)
        
        if not query_terms:
            return 0.0
        
        return matches / len(query_terms)
    
    def _calculate_recency_score(self, row, service: str) -> float:
        """Calculate recency boost"""
        # Find date column
        date = None
        for col in row:
            if isinstance(col, datetime):
                date = col
                break
        
        if not date:
            return 0.5  # Default score
        
        # Calculate days ago
        now = datetime.now()
        days_ago = (now - date).days
        
        # Decay function: score decreases as days increase
        if days_ago <= 1:
            return 1.0
        elif days_ago <= 7:
            return 0.8
        elif days_ago <= 30:
            return 0.6
        elif days_ago <= 90:
            return 0.4
        else:
            return 0.2
    
    async def index_email(
        self,
        user_id: str,
        email_id: str,
        subject: str,
        sender: str,
        body: str,
        received_at: datetime
    ):
        """Index an email for search"""
        text_content = self.embedding_service.prepare_email_text(subject, body)
        embedding = await self.embedding_service.generate_embedding(text_content)
        
        stmt = insert(GmailCache).values(
            user_id=user_id,
            email_id=email_id,
            subject=subject,
            sender=sender,
            body_preview=body[:500] if body else "",
            embedding=embedding,
            received_at=received_at
        )
        
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'email_id'],
            set_={
                'subject': stmt.excluded.subject,
                'sender': stmt.excluded.sender,
                'body_preview': stmt.excluded.body_preview,
                'embedding': stmt.excluded.embedding,
                'received_at': stmt.excluded.received_at,
                'synced_at': datetime.now()
            }
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def index_event(
        self,
        user_id: str,
        event_id: str,
        title: str,
        description: str,
        attendees: List[str],
        start_time: datetime
    ):
        """Index a calendar event for search"""
        text_content = self.embedding_service.prepare_event_text(title, description, attendees)
        embedding = await self.embedding_service.generate_embedding(text_content)
        
        stmt = insert(GCalCache).values(
            user_id=user_id,
            event_id=event_id,
            title=title,
            description=description,
            attendees=attendees,
            embedding=embedding,
            start_time=start_time
        )
        
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'event_id'],
            set_={
                'title': stmt.excluded.title,
                'description': stmt.excluded.description,
                'attendees': stmt.excluded.attendees,
                'embedding': stmt.excluded.embedding,
                'start_time': stmt.excluded.start_time,
                'synced_at': datetime.now()
            }
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
    
    async def index_file(
        self,
        user_id: str,
        file_id: str,
        name: str,
        mime_type: str,
        content_preview: str,
        modified_at: datetime
    ):
        """Index a Drive file for search"""
        text_content = self.embedding_service.prepare_file_text(name, content_preview)
        embedding = await self.embedding_service.generate_embedding(text_content)
        
        stmt = insert(GDriveCache).values(
            user_id=user_id,
            file_id=file_id,
            name=name,
            mime_type=mime_type,
            content_preview=content_preview,
            embedding=embedding,
            modified_at=modified_at
        )
        
        stmt = stmt.on_conflict_do_update(
            index_elements=['user_id', 'file_id'],
            set_={
                'name': stmt.excluded.name,
                'mime_type': stmt.excluded.mime_type,
                'content_preview': stmt.excluded.content_preview,
                'embedding': stmt.excluded.embedding,
                'modified_at': stmt.excluded.modified_at,
                'synced_at': datetime.now()
            }
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
