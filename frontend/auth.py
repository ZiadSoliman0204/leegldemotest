"""
Authentication module for Law Firm AI Assistant
Handles JWT tokens, session management, and user authentication
"""

import jwt
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import secrets
import logging

# Import database manager
try:
    from database import DatabaseManager
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(__file__))
    from database import DatabaseManager

logger = logging.getLogger(__name__)

class AuthManager:
    """Manages user authentication and JWT tokens"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.secret_key = self._get_or_create_secret_key()
        self.algorithm = "HS256"
        self.token_expiration_hours = 24
    
    def _get_or_create_secret_key(self) -> str:
        """Get or create a secret key for JWT signing"""
        if 'jwt_secret_key' not in st.session_state:
            # In production, this should be stored securely (environment variable)
            st.session_state.jwt_secret_key = secrets.token_urlsafe(32)
        return st.session_state.jwt_secret_key
    
    def create_access_token(self, user_data: Dict[str, Any]) -> str:
        """
        Create JWT access token for authenticated user
        
        Args:
            user_data: User information from database
            
        Returns:
            JWT token string
        """
        try:
            payload = {
                'user_id': user_data['id'],
                'username': user_data['username'],
                'role': user_data['role'],
                'exp': datetime.utcnow() + timedelta(hours=self.token_expiration_hours),
                'iat': datetime.utcnow()
            }
            
            token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
            return token
            
        except Exception as error:
            logger.error(f"Error creating access token: {error}")
            return ""
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Decoded token payload if valid, None otherwise
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is not expired
            if datetime.utcnow() > datetime.fromtimestamp(payload['exp']):
                return None
            
            return payload
            
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidTokenError as error:
            logger.warning(f"Invalid token: {error}")
            return None
        except Exception as error:
            logger.error(f"Error verifying token: {error}")
            return None
    
    def authenticate_user(self, username: str, password: str) -> Optional[str]:
        """
        Authenticate user and return JWT token
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            JWT token if authentication successful, None otherwise
        """
        user_data = self.db.authenticate_user(username, password)
        
        if user_data:
            token = self.create_access_token(user_data)
            return token
        
        return None
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get current authenticated user from session
        
        Returns:
            User data if authenticated, None otherwise
        """
        if 'access_token' not in st.session_state:
            return None
        
        token = st.session_state.access_token
        payload = self.verify_token(token)
        
        if payload:
            return {
                'id': payload['user_id'],
                'username': payload['username'],
                'role': payload['role']
            }
        
        # Invalid token, clear session
        self.logout()
        return None
    
    def login(self, username: str, password: str) -> bool:
        """
        Login user and store token in session
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            True if login successful, False otherwise
        """
        token = self.authenticate_user(username, password)
        
        if token:
            st.session_state.access_token = token
            st.session_state.is_authenticated = True
            
            # Store user info for convenience
            user_data = self.get_current_user()
            if user_data:
                st.session_state.current_user = user_data
            
            return True
        
        return False
    
    def logout(self):
        """Logout user and clear session"""
        # Log logout action if user is authenticated
        current_user = self.get_current_user()
        if current_user:
            self.db.log_user_action(
                user_id=current_user['id'],
                username=current_user['username'],
                action="LOGOUT",
                details="User logged out"
            )
        
        # Clear session state
        session_keys_to_clear = [
            'access_token',
            'is_authenticated', 
            'current_user',
            'messages',
            'documents_uploaded'
        ]
        
        for key in session_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
    
    def is_authenticated(self) -> bool:
        """
        Check if user is currently authenticated
        
        Returns:
            True if user is authenticated, False otherwise
        """
        return self.get_current_user() is not None
    
    def require_authentication(self):
        """
        Decorator/function to require authentication for pages
        Redirects to login if not authenticated
        """
        if not self.is_authenticated():
            self.show_login_page()
            st.stop()
    
    def require_admin(self):
        """
        Require admin role for access
        """
        user = self.get_current_user()
        if not user or user['role'] != 'admin':
            st.error("Access denied. Admin privileges required.")
            st.stop()
    
    def show_login_page(self):
        """Display login page"""
        st.title("Legal AI Assistant - Login")
        
        # Center the login form
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown("### Please sign in to continue")
            
            with st.form("login_form"):
                username = st.text_input("Username", placeholder="Enter your username")
                password = st.text_input("Password", type="password", placeholder="Enter your password")
                submit_button = st.form_submit_button("Sign In", use_container_width=True)
                
                if submit_button:
                    if not username or not password:
                        st.error("Please enter both username and password")
                    else:
                        if self.login(username, password):
                            st.success("Login successful! Redirecting...")
                            st.rerun()
                        else:
                            st.error("Invalid username or password")
            
            # Help text
            st.markdown("---")
            st.info("Default admin credentials: username=admin, password=admin123")
            st.caption("Please change the default password after first login")
    
    def show_user_menu(self):
        """Show user menu in sidebar"""
        current_user = self.get_current_user()
        if not current_user:
            return
        
        with st.sidebar:
            st.markdown("---")
            st.markdown(f"**Logged in as:** {current_user['username']}")
            st.markdown(f"**Role:** {current_user['role'].title()}")
            
            if st.button("Logout", use_container_width=True):
                self.logout()
                st.rerun()
            
            # Change password option
            if st.button("Change Password", use_container_width=True):
                st.session_state.show_change_password = True
            
            # Show change password form if requested
            if st.session_state.get('show_change_password', False):
                st.markdown("### Change Password")
                with st.form("change_password_form"):
                    old_password = st.text_input("Current Password", type="password")
                    new_password = st.text_input("New Password", type="password")
                    confirm_password = st.text_input("Confirm New Password", type="password")
                    
                    if st.form_submit_button("Change Password"):
                        if not all([old_password, new_password, confirm_password]):
                            st.error("Please fill in all fields")
                        elif new_password != confirm_password:
                            st.error("New passwords do not match")
                        elif len(new_password) < 6:
                            st.error("Password must be at least 6 characters long")
                        else:
                            if self.db.change_password(current_user['username'], old_password, new_password):
                                st.success("Password changed successfully")
                                st.session_state.show_change_password = False
                                st.rerun()
                            else:
                                st.error("Current password is incorrect")
    
    def log_user_action(self, action: str, details: str = ""):
        """
        Log user action to audit trail
        
        Args:
            action: Action performed
            details: Additional details
        """
        current_user = self.get_current_user()
        if current_user:
            self.db.log_user_action(
                user_id=current_user['id'],
                username=current_user['username'],
                action=action,
                details=details
            ) 