"""
Cache Service - Redis caching for embeddings, intents, and context
"""
from typing import Any, Dict, List, Optional
import json
import hashlib
from datetime import datetime
import structlog
import redis.asyncio as redis

from app.config import settings

logger = structlog.get_logger()


class CacheService:
    """
    Redis-based caching service.
    
    Caches:
    - Embeddings: 1 hour TTL
    - Intent classifications: 1 hour TTL  
    - Conversation context: 24 hour TTL
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.logger = logger.bind(component="cache_service")
    
    # ============ Embedding Cache ============
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding"""
        key = self._embedding_key(text)
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            self.logger.debug("Cache get failed", key=key[:30], error=str(e))
        return None
    
    async def set_embedding(self, text: str, embedding: List[float]):
        """Cache embedding"""
        key = self._embedding_key(text)
        try:
            await self.redis.setex(
                key,
                settings.cache_ttl_embeddings,
                json.dumps(embedding),
            )
        except Exception as e:
            self.logger.debug("Cache set failed", key=key[:30], error=str(e))
    
    def _embedding_key(self, text: str) -> str:
        text_hash = hashlib.md5(text.strip().lower().encode()).hexdigest()
        return f"embedding:{text_hash}"
    
    # ============ Intent Cache ============
    
    async def get_intent(self, query: str, context: Optional[List[str]] = None) -> Optional[Dict]:
        """Get cached intent classification"""
        key = self._intent_key(query, context)
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            self.logger.debug("Intent cache miss", error=str(e))
        return None
    
    async def set_intent(self, query: str, intent: Dict, context: Optional[List[str]] = None):
        """Cache intent classification"""
        key = self._intent_key(query, context)
        try:
            await self.redis.setex(
                key,
                settings.cache_ttl_intent,
                json.dumps(intent),
            )
        except Exception as e:
            self.logger.debug("Intent cache set failed", error=str(e))
    
    def _intent_key(self, query: str, context: Optional[List[str]]) -> str:
        context_str = "|".join(context[-3:]) if context else ""
        content = f"{query}|{context_str}"
        return f"intent:{hashlib.md5(content.encode()).hexdigest()}"
    
    # ============ Conversation Context ============
    
    async def get_context(self, conversation_id: str) -> List[str]:
        """Get conversation context (last 5 queries)"""
        key = f"context:{conversation_id}"
        try:
            data = await self.redis.lrange(key, 0, 4)
            return [item.decode() if isinstance(item, bytes) else item for item in data]
        except Exception as e:
            self.logger.debug("Context get failed", error=str(e))
        return []
    
    async def add_to_context(self, conversation_id: str, query: str):
        """Add query to conversation context"""
        key = f"context:{conversation_id}"
        try:
            await self.redis.lpush(key, query)
            await self.redis.ltrim(key, 0, 4)  # Keep only last 5
            await self.redis.expire(key, settings.cache_ttl_context)
        except Exception as e:
            self.logger.debug("Context add failed", error=str(e))
    
    # ============ Cache Statistics ============
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        try:
            info = await self.redis.info("stats")
            return {
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": self._calculate_hit_rate(info),
            }
        except Exception as e:
            self.logger.debug("Stats get failed", error=str(e))
            return {}
    
    def _calculate_hit_rate(self, info: Dict) -> float:
        hits = info.get("keyspace_hits", 0)
        misses = info.get("keyspace_misses", 0)
        total = hits + misses
        return round(hits / total, 2) if total > 0 else 0.0


class RateLimiter:
    """
    Rate limiter using Redis sliding window.
    
    Default: 100 queries per user per hour
    """
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.logger = logger.bind(component="rate_limiter")
        self.limit = settings.rate_limit_queries_per_hour
        self.window = 3600  # 1 hour in seconds
    
    async def check_rate_limit(self, user_id: str) -> tuple[bool, int]:
        """
        Check if user is within rate limit.
        
        Returns:
            Tuple of (allowed, remaining_requests)
        """
        key = f"ratelimit:{user_id}"
        now = datetime.now().timestamp()
        window_start = now - self.window
        
        try:
            # Remove old entries
            await self.redis.zremrangebyscore(key, 0, window_start)
            
            # Count current requests
            current_count = await self.redis.zcard(key)
            
            if current_count >= self.limit:
                self.logger.warning("Rate limit exceeded", user_id=user_id, count=current_count)
                return False, 0
            
            # Add new request
            await self.redis.zadd(key, {str(now): now})
            await self.redis.expire(key, self.window)
            
            remaining = self.limit - current_count - 1
            return True, remaining
            
        except Exception as e:
            self.logger.error("Rate limit check failed", error=str(e))
            # Fail open
            return True, self.limit
    
    async def get_retry_after(self, user_id: str) -> int:
        """Get seconds until rate limit resets"""
        key = f"ratelimit:{user_id}"
        
        try:
            # Get oldest entry
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                oldest_time = oldest[0][1]
                reset_time = oldest_time + self.window
                now = datetime.now().timestamp()
                return max(0, int(reset_time - now))
        except Exception:
            pass
        
        return 0
