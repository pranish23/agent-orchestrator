"""
API routers
"""
from app.api.query import router as query_router
from app.api.auth import router as auth_router
from app.api.sync import router as sync_router
from app.api.search import router as search_router

__all__ = ["query_router", "auth_router", "sync_router", "search_router"]
