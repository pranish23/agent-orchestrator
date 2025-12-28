"""
Application configuration using Pydantic Settings
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Environment
    environment: str = "development"
    debug: bool = True
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/orchestrator"
    database_sync_url: str = "postgresql://postgres:postgres@db:5432/orchestrator"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # LLM Settings
    llm_provider: str = "openai"  # openai or gemini
    
    # OpenAI
    openai_api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-small"
    llm_model: str = "gpt-4o-mini"
    
    # Gemini
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"
    gemini_embedding_model: str = "models/embedding-001"
    
    # Rate Limiting
    rate_limit_queries_per_hour: int = 100
    
    # Cache TTL (seconds)
    cache_ttl_embeddings: int = 3600  # 1 hour
    cache_ttl_intent: int = 3600  # 1 hour
    cache_ttl_context: int = 86400  # 24 hours
    
    # Sync Settings
    sync_interval_minutes: int = 15
    
    # Google OAuth
    google_client_id: Optional[str] = None
    google_client_secret: Optional[str] = None
    google_redirect_uri: str = "http://localhost:8000/api/v1/auth/callback"
    
    # Performance
    max_query_timeout_seconds: int = 30
    embedding_batch_size: int = 100
    search_top_k: int = 10
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    @property
    def embedding_dimensions(self) -> int:
        """Return dimensions based on provider"""
        return 1536 if self.llm_provider.lower() == "openai" else 768


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
