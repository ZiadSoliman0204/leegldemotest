"""
Authentication routes for Law Firm AI Assistant Backend
Provides JWT token generation for API access
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import Dict, Any
import sys
from pathlib import Path

# Add frontend to path to access the database
sys.path.append(str(Path(__file__).parent.parent.parent / "frontend"))

try:
    from database import DatabaseManager
except ImportError:
    class DatabaseManager:
        def authenticate_user(self, **kwargs):
            return None

from ..auth import create_access_token, get_current_user

router = APIRouter()

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

@router.post("/login", response_model=LoginResponse)
async def login_for_access_token(login_request: LoginRequest):
    """
    Authenticate user and return JWT token for API access
    This allows frontend users to get tokens for direct API calls
    """
    db_manager = DatabaseManager()
    
    # Authenticate user using existing frontend system
    user_data = db_manager.authenticate_user(
        username=login_request.username,
        password=login_request.password,
        ip_address="api_login",
        user_agent="backend_api",
        session_id="api_session"
    )
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create JWT token
    access_token = create_access_token(user_data)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": user_data["id"],
            "username": user_data["username"],
            "role": user_data.get("role", "user")
        }
    )

@router.get("/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Get current user information from token
    """
    return {
        "user": current_user,
        "authenticated": True
    }

@router.get("/validate")
async def validate_token(current_user: dict = Depends(get_current_user)):
    """
    Validate JWT token - useful for testing
    """
    return {
        "valid": True,
        "user": current_user,
        "auth_type": current_user.get("auth_type", "jwt")
    } 