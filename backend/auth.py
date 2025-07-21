"""
Backend Authentication module for Law Firm AI Assistant
Integrates with existing frontend user system and provides API key support for n8n
"""

import os
import sys
import sqlite3
import hashlib
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from pathlib import Path

# Add frontend to path to access the database
sys.path.append(str(Path(__file__).parent.parent / "frontend"))

try:
    from database import DatabaseManager
except ImportError:
    # Fallback if frontend database is not available
    class DatabaseManager:
        def authenticate_user(self, **kwargs):
            return None
        def get_users(self):
            return []

# Security scheme
security = HTTPBearer()

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_HOURS = 24

# API Keys for service authentication (n8n, etc.)
API_KEYS = {
    os.getenv("N8N_API_KEY", "n8n-secret-key-change-this"): {
        "service": "n8n",
        "role": "admin",
        "description": "n8n workflow automation"
    },
    os.getenv("INTERNAL_API_KEY", "internal-secret-key"): {
        "service": "internal",
        "role": "admin", 
        "description": "Internal service integration"
    }
}

class BackendAuthManager:
    """Backend authentication manager that integrates with frontend user system"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """Create JWT access token for user"""
        to_encode = {
            "user_id": user_data["id"],
            "username": user_data["username"],
            "role": user_data.get("role", "user"),
            "exp": datetime.utcnow() + timedelta(hours=JWT_ACCESS_TOKEN_EXPIRE_HOURS)
        }
        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return user data"""
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Verify user still exists and is active
            users = self.db_manager.get_users()
            for user in users:
                if user["id"] == payload["user_id"] and user.get("is_active", True):
                    return {
                        "user_id": payload["user_id"],
                        "username": payload["username"],
                        "role": payload.get("role", "user"),
                        "auth_type": "jwt"
                    }
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    def verify_api_key(self, api_key: str) -> Dict[str, Any]:
        """Verify API key and return service data"""
        if api_key in API_KEYS:
            service_info = API_KEYS[api_key]
            return {
                "user_id": 0,
                "username": service_info["service"],
                "role": service_info["role"],
                "service": service_info["service"],
                "description": service_info["description"],
                "auth_type": "api_key"
            }
        return None
    
    def authenticate_request(self, credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
        """Authenticate request using JWT token or API key"""
        token = credentials.credentials
        
        # Try API key first (for n8n and other services)
        api_key_result = self.verify_api_key(token)
        if api_key_result:
            return api_key_result
        
        # Try JWT token (for regular users)
        return self.verify_jwt_token(token)

# Global auth manager instance
auth_manager = BackendAuthManager()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Get current authenticated user or service"""
    try:
        return auth_manager.authenticate_request(credentials)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}"
        )

def require_admin(current_user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """Require admin privileges"""
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

def get_current_user_optional(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Optional[Dict[str, Any]]:
    """Get current user but don't require authentication (for optional auth endpoints)"""
    try:
        return auth_manager.authenticate_request(credentials)
    except:
        return None

# Legacy function for backward compatibility
def create_access_token(user_data: Dict[str, Any]) -> str:
    """Create JWT access token - backward compatibility"""
    return auth_manager.create_access_token(user_data) 