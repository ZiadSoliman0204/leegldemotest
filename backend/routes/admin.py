"""
Admin routes for Law Firm AI Assistant
Handles administrative operations like user management
Enhanced with comprehensive audit logging and role-based access control
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

# Since this is backend, we'll simulate the database and auth operations
# In a real implementation, you'd import proper auth and database modules

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class ChangeRoleRequest(BaseModel):
    user_id: int
    new_role: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    created_at: str
    is_active: bool
    last_login: Optional[str] = None
    failed_login_attempts: int = 0


def require_admin():
    """
    Dependency to ensure the user has admin privileges
    In a real implementation, this would decode JWT token and verify role
    """
    # This is a placeholder - in real implementation you'd:
    # 1. Decode JWT token from Authorization header
    # 2. Verify token is valid
    # 3. Check user role is 'admin'
    # 4. Return user info or raise HTTPException
    
    # For now, we'll simulate this check
    return {"id": 1, "username": "admin", "role": "admin"}


def log_admin_audit(
    action_type: str,
    status: str,
    details: str,
    admin_user: dict,
    ip_address: str = "",
    resource: str = "",
    severity_level: str = "INFO"
):
    """Log admin actions for audit trail"""
    try:
        logger.info(
            f"ADMIN_AUDIT: action_type={action_type}, status={status}, "
            f"admin={admin_user['username']}, resource={resource}, "
            f"ip_address={ip_address}, severity_level={severity_level}, "
            f"details={details}"
        )
    except Exception as e:
        logger.error(f"Failed to log admin audit event: {e}")


@router.post("/users", response_model=dict)
async def create_user(
    request: CreateUserRequest,
    current_admin: dict = Depends(require_admin)
):
    """
    Create a new user (admin only)
    """
    try:
        # Validate role
        if request.role not in ['admin', 'user']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be 'admin' or 'user'"
            )
        
        # Validate username
        if len(request.username) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username must be at least 3 characters long"
            )
        
        # Validate password
        if len(request.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Log user creation attempt
        log_admin_audit(
            action_type="USER_CREATE_ATTEMPT",
            status="initiated",
            details=f"Admin attempting to create user '{request.username}' with role '{request.role}'",
            admin_user=current_admin,
            resource=f"user:{request.username}",
            severity_level="INFO"
        )
        
        # In real implementation, create user in database here
        # For now, simulate success
        
        # Log successful creation
        log_admin_audit(
            action_type="USER_CREATE_SUCCESS",
            status="success",
            details=f"User '{request.username}' created successfully with role '{request.role}'",
            admin_user=current_admin,
            resource=f"user:{request.username}",
            severity_level="INFO"
        )
        
        return {
            "success": True,
            "message": f"User '{request.username}' created successfully",
            "user_id": 123  # Placeholder ID
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_admin_audit(
            action_type="USER_CREATE_ERROR",
            status="error",
            details=f"User creation failed: {str(e)}",
            admin_user=current_admin,
            resource=f"user:{request.username}",
            severity_level="ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/users", response_model=List[UserResponse])
async def get_all_users(current_admin: dict = Depends(require_admin)):
    """
    Get all users (admin only)
    """
    try:
        log_admin_audit(
            action_type="USER_LIST_ACCESS",
            status="success",
            details="Admin accessed user list",
            admin_user=current_admin,
            resource="user_list",
            severity_level="INFO"
        )
        
        # In real implementation, fetch from database
        # Return placeholder data for now
        return [
            {
                "id": 1,
                "username": "admin",
                "role": "admin",
                "created_at": "2024-01-01T00:00:00",
                "is_active": True,
                "last_login": "2024-01-20T10:00:00",
                "failed_login_attempts": 0
            }
        ]
        
    except Exception as e:
        log_admin_audit(
            action_type="USER_LIST_ERROR",
            status="error",
            details=f"Failed to retrieve user list: {str(e)}",
            admin_user=current_admin,
            resource="user_list",
            severity_level="ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve users"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_admin: dict = Depends(require_admin)
):
    """
    Delete a user (admin only)
    """
    try:
        # Prevent admin from deleting themselves
        if user_id == current_admin["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )
        
        log_admin_audit(
            action_type="USER_DELETE_ATTEMPT",
            status="initiated",
            details=f"Admin attempting to delete user ID {user_id}",
            admin_user=current_admin,
            resource=f"user_id:{user_id}",
            severity_level="INFO"
        )
        
        # In real implementation, delete from database here
        # For now, simulate success
        
        log_admin_audit(
            action_type="USER_DELETE_SUCCESS",
            status="success",
            details=f"User ID {user_id} deleted successfully",
            admin_user=current_admin,
            resource=f"user_id:{user_id}",
            severity_level="INFO"
        )
        
        return {
            "success": True,
            "message": "User deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_admin_audit(
            action_type="USER_DELETE_ERROR",
            status="error",
            details=f"User deletion failed: {str(e)}",
            admin_user=current_admin,
            resource=f"user_id:{user_id}",
            severity_level="ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


@router.put("/users/{user_id}/role")
async def change_user_role(
    user_id: int,
    request: ChangeRoleRequest,
    current_admin: dict = Depends(require_admin)
):
    """
    Change a user's role (admin only)
    """
    try:
        # Validate role
        if request.new_role not in ['admin', 'user']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Must be 'admin' or 'user'"
            )
        
        log_admin_audit(
            action_type="ROLE_CHANGE_ATTEMPT",
            status="initiated",
            details=f"Admin attempting to change user ID {user_id} role to '{request.new_role}'",
            admin_user=current_admin,
            resource=f"user_id:{user_id}",
            severity_level="INFO"
        )
        
        # In real implementation, update database here
        # For now, simulate success
        
        log_admin_audit(
            action_type="ROLE_CHANGE_SUCCESS",
            status="success",
            details=f"User ID {user_id} role changed to '{request.new_role}'",
            admin_user=current_admin,
            resource=f"user_id:{user_id}",
            severity_level="INFO"
        )
        
        return {
            "success": True,
            "message": f"User role changed to '{request.new_role}'"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        log_admin_audit(
            action_type="ROLE_CHANGE_ERROR",
            status="error",
            details=f"Role change failed: {str(e)}",
            admin_user=current_admin,
            resource=f"user_id:{user_id}",
            severity_level="ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change user role"
        )


@router.put("/users/{user_id}/unlock")
async def unlock_user_account(
    user_id: int,
    current_admin: dict = Depends(require_admin)
):
    """
    Unlock a user account by resetting failed login attempts (admin only)
    """
    try:
        log_admin_audit(
            action_type="ACCOUNT_UNLOCK_ATTEMPT",
            status="initiated",
            details=f"Admin attempting to unlock user ID {user_id}",
            admin_user=current_admin,
            resource=f"user_id:{user_id}",
            severity_level="INFO"
        )
        
        # In real implementation, reset failed_login_attempts in database
        # For now, simulate success
        
        log_admin_audit(
            action_type="ACCOUNT_UNLOCK_SUCCESS",
            status="success",
            details=f"User ID {user_id} account unlocked successfully",
            admin_user=current_admin,
            resource=f"user_id:{user_id}",
            severity_level="INFO"
        )
        
        return {
            "success": True,
            "message": "User account unlocked successfully"
        }
        
    except Exception as e:
        log_admin_audit(
            action_type="ACCOUNT_UNLOCK_ERROR",
            status="error",
            details=f"Account unlock failed: {str(e)}",
            admin_user=current_admin,
            resource=f"user_id:{user_id}",
            severity_level="ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to unlock user account"
        )


@router.get("/stats")
async def get_admin_stats(current_admin: dict = Depends(require_admin)):
    """
    Get administrative statistics (admin only)
    """
    try:
        log_admin_audit(
            action_type="ADMIN_STATS_ACCESS",
            status="success",
            details="Admin accessed administrative statistics",
            admin_user=current_admin,
            resource="admin_stats",
            severity_level="INFO"
        )
        
        # In real implementation, calculate from database
        return {
            "total_users": 5,
            "admin_users": 1,
            "regular_users": 4,
            "locked_accounts": 0,
            "total_documents": 10,
            "total_chat_sessions": 50,
            "system_uptime": "5 days",
            "last_backup": "2024-01-20T02:00:00"
        }
        
    except Exception as e:
        log_admin_audit(
            action_type="ADMIN_STATS_ERROR",
            status="error",
            details=f"Failed to retrieve admin stats: {str(e)}",
            admin_user=current_admin,
            resource="admin_stats",
            severity_level="ERROR"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        ) 