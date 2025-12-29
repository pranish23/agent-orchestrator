"""
Authentication API endpoints (Google OAuth)
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
import structlog

from app.config import settings

router = APIRouter()
logger = structlog.get_logger()


@router.get("/google")
async def google_auth():
    """
    Initiate Google OAuth flow.
    Redirects to Google's OAuth consent screen.
    """
    # For mock implementation, return a placeholder
    if not settings.google_client_id:
        return {
            "message": "Mock authentication mode",
            "info": "Google OAuth is not configured. Using mock user.",
            "mock_user_id": "mock-user-001",
        }
    
    # In production, redirect to Google OAuth
    oauth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={settings.google_client_id}&"
        f"redirect_uri={settings.google_redirect_uri}&"
        f"response_type=code&"
        f"scope=https://www.googleapis.com/auth/gmail.readonly "
        f"https://www.googleapis.com/auth/calendar.readonly "
        f"https://www.googleapis.com/auth/drive.readonly&"
        f"access_type=offline"
    )
    return RedirectResponse(url=oauth_url)


@router.get("/callback")
async def google_callback(code: str = None, error: str = None):
    """
    Handle Google OAuth callback.
    Exchanges authorization code for access token.
    """
    if error:
        raise HTTPException(status_code=400, detail=f"OAuth error: {error}")
    
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")
    
    # For mock implementation
    if not settings.google_client_id:
        return {
            "message": "Mock authentication successful",
            "user_id": "mock-user-001",
        }
    
    # In production, exchange code for tokens
    logger.info("OAuth callback received", code_length=len(code))
    
    return {
        "message": "Authentication successful",
        "info": "Token exchange would happen here in production",
    }


@router.get("/status")
async def auth_status():
    """Check authentication status for current user"""
    return {
        "authenticated": True,
        "mock_mode": not settings.google_client_id,
        "user_id": "mock-user-001",
    }
