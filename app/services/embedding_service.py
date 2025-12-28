"""
Embedding Service - Generate and manage vector embeddings
"""
import asyncio
from typing import Any, Dict, List, Optional
import hashlib
from datetime import datetime
import structlog
import numpy as np
from app.config import settings
from app.services.llm_provider import get_llm_provider

logger = structlog.get_logger()


class EmbeddingService:
    """
    Generates and manages vector embeddings for semantic search.
    
    Uses OpenAI's text-embedding-3-small model (1536 dimensions)
    with caching support via Redis.
    """
    
    def __init__(self, redis_client=None):
        self.provider = get_llm_provider(settings)
        self.redis = redis_client
        self.logger = logger.bind(component="embedding_service")
        self.dimensions = 1536 if settings.llm_provider == "openai" else 768 # Gemini embeddings are 768
        
        # Local cache for development
        self._cache: Dict[str, List[float]] = {}
    
    async def generate_embedding(
        self,
        text: str,
        use_cache: bool = True
    ) -> Optional[List[float]]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            use_cache: Whether to use cache
            
        Returns:
            1536-dimensional embedding vector
        """
        if not text or not text.strip():
            return None
        
        # Check cache
        cache_key = self._get_cache_key(text)
        if use_cache:
            cached = await self._get_cached(cache_key)
            if cached:
                return cached
        
        # Generate embedding
        if self.provider:
            try:
                embedding = await self.provider.generate_embedding(text)
                if use_cache:
                    await self._set_cached(cache_key, embedding)
                return embedding
            except Exception as e:
                self.logger.warning("LLM embedding failed", error=str(e), exc_info=True)
        
        # Fallback to mock embedding
        embedding = self._generate_mock_embedding(text)
        if use_cache:
            await self._set_cached(cache_key, embedding)
        return embedding
    
    async def generate_embeddings_batch(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> List[Optional[List[float]]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to embed
            use_cache: Whether to use cache
            
        Returns:
            List of embeddings (None for invalid texts)
        """
        results = []
        uncached_indices = []
        uncached_texts = []
        
        # Check cache first
        for i, text in enumerate(texts):
            if not text or not text.strip():
                results.append(None)
                continue
            
            cache_key = self._get_cache_key(text)
            if use_cache:
                cached = await self._get_cached(cache_key)
                if cached:
                    results.append(cached)
                    continue
            
            results.append(None)  # Placeholder
            uncached_indices.append(i)
            uncached_texts.append(text)
        
        # Generate embeddings for uncached texts
        if uncached_texts:
            if self.provider:
                try:
                    # Generic batch processing if provider doesn't support it directly
                    # OpenAI supports batch, Gemini doesn't (officially in standard API as much)
                    # For simplicity, we'll do them sequentially or parallel
                    tasks = [self.provider.generate_embedding(t) for t in uncached_texts]
                    embeddings = await asyncio.gather(*tasks)
                    
                    for idx, embedding in zip(uncached_indices, embeddings):
                        results[idx] = embedding
                        if use_cache:
                            await self._set_cached(self._get_cache_key(texts[idx]), embedding)
                except Exception as e:
                    self.logger.warning("Batch embedding failed", error=str(e), exc_info=True)
                    # Fallback to mock
                    for idx, text in zip(uncached_indices, uncached_texts):
                        embedding = self._generate_mock_embedding(text)
                        results[idx] = embedding
            else:
                for idx, text in zip(uncached_indices, uncached_texts):
                    embedding = self._generate_mock_embedding(text)
                    results[idx] = embedding
        
        return results
    
    
    def _generate_mock_embedding(self, text: str) -> List[float]:
        """
        Generate a deterministic mock embedding for testing.
        
        Uses a hash-based approach to generate consistent embeddings
        for the same text.
        """
        # Create deterministic seed from text
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        seed = int(text_hash[:8], 16)
        np.random.seed(seed)
        
        # Generate normalized random vector
        embedding = np.random.randn(self.dimensions)
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding.tolist()
    
    async def _get_cached(self, key: str) -> Optional[List[float]]:
        """Get embedding from cache"""
        # Try Redis first
        if self.redis:
            try:
                import json
                data = await self.redis.get(f"embedding:{key}")
                if data:
                    return json.loads(data)
            except Exception as e:
                self.logger.debug("Redis cache miss", key=key[:20])
        
        # Fall back to local cache
        return self._cache.get(key)
    
    async def _set_cached(self, key: str, embedding: List[float]):
        """Store embedding in cache"""
        # Store in Redis
        if self.redis:
            try:
                import json
                await self.redis.setex(
                    f"embedding:{key}",
                    settings.cache_ttl_embeddings,
                    json.dumps(embedding),
                )
            except Exception as e:
                self.logger.debug("Redis cache set failed", error=str(e))
        
        # Also store locally
        self._cache[key] = embedding
    
    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text"""
        return hashlib.md5(text.strip().lower().encode()).hexdigest()
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    
    def prepare_email_text(self, subject: str, body: str) -> str:
        """Prepare email text for embedding"""
        body_preview = body[:500] if body else ""
        return f"Subject: {subject}\n\n{body_preview}"
    
    def prepare_event_text(self, title: str, description: str, attendees: List[str] = None) -> str:
        """Prepare calendar event text for embedding"""
        parts = [f"Event: {title}"]
        if description:
            parts.append(f"Description: {description}")
        if attendees:
            parts.append(f"Attendees: {', '.join(attendees)}")
        return "\n".join(parts)
    
    def prepare_file_text(self, name: str, content_preview: str = None) -> str:
        """Prepare file text for embedding"""
        parts = [f"File: {name}"]
        if content_preview:
            parts.append(f"Content: {content_preview[:500]}")
        return "\n".join(parts)
