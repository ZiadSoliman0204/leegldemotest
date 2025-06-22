"""
Authentication module for Law Firm AI Assistant
Handles user authentication, session management, and access control
Enhanced with comprehensive audit logging and security features
"""

import streamlit as st
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

try:
    from database import DatabaseManager
except ImportError:
    from .database import DatabaseManager

logger = logging.getLogger(__name__)

class AuthManager:
    """
    Manages user authentication with enhanced security and audit logging
    Features: Session management, failed login tracking, comprehensive audit logs
    """
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.session_timeout = timedelta(hours=8)  # 8-hour session timeout
        self.max_failed_attempts = 5  # Lock account after 5 failed attempts
        self._initialize_session_security()
    
    def _initialize_session_security(self):
        """Initialize session security parameters"""
        if 'session_initialized' not in st.session_state:
            st.session_state.session_initialized = True
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.session_start_time = datetime.now()
            st.session_state.last_activity = datetime.now()
    
    def _get_client_ip(self) -> str:
        """Get client IP address for audit logging"""
        try:
            if hasattr(st, 'context') and hasattr(st.context, 'headers'):
                forwarded_for = st.context.headers.get('X-Forwarded-For')
                if forwarded_for:
                    return forwarded_for.split(',')[0].strip()
                
                real_ip = st.context.headers.get('X-Real-IP')
                if real_ip:
                    return real_ip
            
            return "127.0.0.1"  # Fallback for local development
        except Exception:
            return "unknown"
    
    def _get_user_agent(self) -> str:
        """Get user agent for audit logging"""
        try:
            if hasattr(st, 'context') and hasattr(st.context, 'headers'):
                return st.context.headers.get('User-Agent', 'unknown')
            return "unknown"
        except Exception:
            return "unknown"
    
    def _check_session_timeout(self) -> bool:
        """Check if current session has timed out"""
        if 'last_activity' not in st.session_state:
            return True
        
        last_activity = st.session_state.last_activity
        if isinstance(last_activity, str):
            last_activity = datetime.fromisoformat(last_activity)
        
        return datetime.now() - last_activity > self.session_timeout
    
    def _update_last_activity(self):
        """Update last activity timestamp"""
        st.session_state.last_activity = datetime.now()
    
    def _is_account_locked(self, username: str) -> bool:
        """Check if account is locked due to too many failed attempts"""
        try:
            users = self.db_manager.get_users()
            for user in users:
                if user['username'] == username:
                    return user.get('failed_login_attempts', 0) >= self.max_failed_attempts
            return False
        except Exception as e:
            logger.error(f"Error checking account lock status: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """
        Authenticate user with enhanced security and audit logging
        
        Args:
            username: User's username
            password: User's password
            
        Returns:
            True if authentication successful, False otherwise
        """
        ip_address = self._get_client_ip()
        user_agent = self._get_user_agent()
        session_id = st.session_state.get('session_id', 'unknown')
        
        # Check if account is locked
        if self._is_account_locked(username):
            self.db_manager.log_audit_event(
                user_id=None,
                username=username,
                action_type="LOGIN_BLOCKED_LOCKED_ACCOUNT",
                resource="authentication",
                status="failure",
                details=f"Login attempt blocked - account locked due to {self.max_failed_attempts}+ failed attempts",
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                severity_level="WARNING"
            )
            
            st.error(f"Account locked due to too many failed login attempts. Please contact an administrator.")
            return False
        
        # Attempt authentication
        user_data = self.db_manager.authenticate_user(
            username=username,
            password=password,
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=session_id
        )
        
        if user_data:
            # Successful authentication
            st.session_state.authenticated = True
            st.session_state.user = user_data
            st.session_state.login_time = datetime.now()
            self._update_last_activity()
            
            # Log successful session creation
            self.db_manager.log_audit_event(
                user_id=user_data['id'],
                username=username,
                action_type="SESSION_CREATED",
                resource="user_session",
                status="success",
                details=f"New user session created. Session timeout: {self.session_timeout}",
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                severity_level="INFO"
            )
            
            st.success(f"Welcome back, {user_data['username']}!")
            return True
        else:
            # Failed authentication - already logged by DatabaseManager
            return False
    
    def logout_user(self):
        """
        Logout user with comprehensive audit logging
        """
        current_user = self.get_current_user()
        ip_address = self._get_client_ip()
        session_id = st.session_state.get('session_id', 'unknown')
        
        if current_user:
            # Calculate session duration
            login_time = st.session_state.get('login_time', datetime.now())
            if isinstance(login_time, str):
                login_time = datetime.fromisoformat(login_time)
            session_duration = datetime.now() - login_time
            
            # Log logout event
            self.db_manager.log_audit_event(
                user_id=current_user['id'],
                username=current_user['username'],
                action_type="USER_LOGOUT",
                resource="user_session",
                status="success",
                details=f"User logged out. Session duration: {session_duration}",
                ip_address=ip_address,
                session_id=session_id,
                severity_level="INFO"
            )
            
            # Log session termination
            self.db_manager.log_audit_event(
                user_id=current_user['id'],
                username=current_user['username'],
                action_type="SESSION_TERMINATED",
                resource="user_session",
                status="success",
                details=f"User session terminated normally. Total duration: {session_duration}",
                ip_address=ip_address,
                session_id=session_id,
                severity_level="INFO"
            )
        
        # Clear session state
        session_keys_to_clear = ['authenticated', 'user', 'login_time', 'last_activity']
        for key in session_keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        # Generate new session ID for security
        st.session_state.session_id = str(uuid.uuid4())
        
        st.success("You have been logged out successfully.")
        st.rerun()
    
    def is_authenticated(self) -> bool:
        """
        Check if user is authenticated and session is valid
        
        Returns:
            True if user is authenticated and session is valid
        """
        if not st.session_state.get('authenticated', False):
            return False
        
        # Check session timeout
        if self._check_session_timeout():
            current_user = self.get_current_user()
            if current_user:
                # Log session timeout
                self.db_manager.log_audit_event(
                    user_id=current_user['id'],
                    username=current_user['username'],
                    action_type="SESSION_TIMEOUT",
                    resource="user_session",
                    status="expired",
                    details=f"User session expired after {self.session_timeout}",
                    ip_address=self._get_client_ip(),
                    session_id=st.session_state.get('session_id', 'unknown'),
                    severity_level="INFO"
                )
            
            # Clear expired session
            self.logout_user()
            st.warning("Your session has expired. Please log in again.")
            return False
        
        # Update last activity
        self._update_last_activity()
        return True
    
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """
        Get current authenticated user data
        
        Returns:
            User data dictionary if authenticated, None otherwise
        """
        if self.is_authenticated():
            return st.session_state.get('user')
        return None
    
    def require_admin(self) -> bool:
        """
        Check if current user has admin privileges
        
        Returns:
            True if user is admin, False otherwise
        """
        current_user = self.get_current_user()
        if not current_user:
            return False
        
        is_admin = current_user.get('role') == 'admin'
        
        if not is_admin:
            # Log unauthorized admin access attempt
            self.db_manager.log_audit_event(
                user_id=current_user['id'],
                username=current_user['username'],
                action_type="UNAUTHORIZED_ADMIN_ACCESS",
                resource="admin_area",
                status="failure",
                details="Non-admin user attempted to access admin functionality",
                ip_address=self._get_client_ip(),
                session_id=st.session_state.get('session_id', 'unknown'),
                severity_level="WARNING"
            )
        
        return is_admin
    
    def check_admin_access(self, action_description: str = "access admin features") -> bool:
        """
        Check admin access and show appropriate error messages
        Returns True if user is admin, False otherwise
        """
        current_user = self.get_current_user()
        
        if not current_user:
            st.error("🔒 Please log in to access this feature.")
            return False
        
        if current_user.get('role') != 'admin':
            # Log unauthorized access attempt
            self.db_manager.log_audit_event(
                user_id=current_user['id'],
                username=current_user['username'],
                action_type="UNAUTHORIZED_ACCESS_ATTEMPT",
                resource="admin_features",
                status="failure",
                details=f"Non-admin user attempted to {action_description}",
                ip_address=self._get_client_ip(),
                session_id=st.session_state.get('session_id', 'unknown'),
                severity_level="WARNING"
            )
            
            st.error("🔒 Access denied. Administrator privileges required.")
            st.info("If you believe you should have admin access, please contact your system administrator.")
            return False
        
        return True
    
    def log_user_action(self, action: str, details: str = ""):
        """
        Legacy method for backward compatibility
        Logs user actions using the enhanced audit system
        
        Args:
            action: Action type
            details: Action details
        """
        current_user = self.get_current_user()
        
        self.db_manager.log_audit_event(
            user_id=current_user['id'] if current_user else None,
            username=current_user['username'] if current_user else 'anonymous',
            action_type=action,
            resource="user_action",
            status="success",
            details=details,
            ip_address=self._get_client_ip(),
            user_agent=self._get_user_agent(),
            session_id=st.session_state.get('session_id', 'unknown'),
            severity_level="INFO"
        )
    
    def show_login_page(self):
        """
        Display login page with enhanced security features
        """
        st.title("Law Firm AI Assistant")
        st.markdown("### Secure Login Portal")
        
        # Check for session hijacking attempts
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        
        with st.form("login_form"):
            st.markdown("#### Please enter your credentials")
            
            username = st.text_input(
                "Username",
                placeholder="Enter your username",
                help="Use your assigned username"
            )
            
            password = st.text_input(
                "Password",
                type="password",
                placeholder="Enter your password",
                help="Enter your secure password"
            )
            
            login_submitted = st.form_submit_button("🔑 Sign In", use_container_width=True)
            
            if login_submitted:
                if not username or not password:
                    st.error("Please enter both username and password")
                    return
                
                # Log login attempt
                ip_address = self._get_client_ip()
                self.db_manager.log_audit_event(
                    user_id=None,
                    username=username,
                    action_type="LOGIN_ATTEMPT",
                    resource="authentication",
                    status="initiated",
                    details=f"User attempted login from IP: {ip_address}",
                    ip_address=ip_address,
                    user_agent=self._get_user_agent(),
                    session_id=st.session_state.get('session_id', 'unknown'),
                    severity_level="INFO"
                )
                
                if self.authenticate_user(username, password):
                    st.rerun()
        
        # Security information
        st.markdown("---")
        with st.expander("Security Information"):
            st.markdown("""
            **Security Features:**
            - Secure password authentication with bcrypt hashing
            - Session timeout after 8 hours of inactivity  
            - Account lockout after 5 failed login attempts
            - Comprehensive audit logging of all activities
            - IP address tracking and session management
            - Encrypted sensitive data storage
            
            **Default Admin Credentials:**
            - Username: `admin`
            - Password: `admin123`
            - **Please change the default password immediately after first login**
            """)
    
    def show_user_menu(self):
        """
        Display user menu with profile and security options
        """
        current_user = self.get_current_user()
        if not current_user:
            return
        
        with st.sidebar:
            st.markdown("---")
            
            # User info with role badge
            role_badge = "🔑 Admin" if current_user['role'] == 'admin' else "👤 User"
            st.markdown(f"**👋 {current_user['username']}**")
            st.markdown(f"**Role:** {role_badge}")
            
            # Show session info
            login_time = st.session_state.get('login_time', datetime.now())
            if isinstance(login_time, str):
                login_time = datetime.fromisoformat(login_time)
            session_duration = datetime.now() - login_time
            hours, remainder = divmod(session_duration.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            st.markdown(f"**Session:** {hours}h {minutes}m")
            
            # User actions
            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("Change Password", use_container_width=True):
                    st.session_state.show_change_password = True
                    st.rerun()
            
            with col2:
                if st.button("Logout", use_container_width=True):
                    self.logout_user()
            
            # Change password form
            if st.session_state.get('show_change_password', False):
                self._show_change_password_form()
    
    def _show_change_password_form(self):
        """Display password change form with security validation"""
        st.markdown("---")
        st.markdown("#### Change Password")
        
        with st.form("change_password_form"):
            current_password = st.text_input(
                "Current Password",
                type="password",
                help="Enter your current password"
            )
            
            new_password = st.text_input(
                "New Password", 
                type="password",
                help="Enter a strong new password (min 8 characters)"
            )
            
            confirm_password = st.text_input(
                "Confirm New Password",
                type="password",
                help="Confirm your new password"
            )
            
            col1, col2 = st.columns(2)
            
            with col1:
                change_submitted = st.form_submit_button("Update", use_container_width=True)
            
            with col2:
                cancel_change = st.form_submit_button("Cancel", use_container_width=True)
            
            if cancel_change:
                st.session_state.show_change_password = False
                st.rerun()
            
            if change_submitted:
                current_user = self.get_current_user()
                if not current_user:
                    st.error("Authentication error. Please log in again.")
                    return
                
                # Validate inputs
                if not all([current_password, new_password, confirm_password]):
                    st.error("Please fill in all password fields")
                    return
                
                if new_password != confirm_password:
                    st.error("New passwords do not match")
                    return
                
                if len(new_password) < 8:
                    st.error("New password must be at least 8 characters long")
                    return
                
                if new_password == current_password:
                    st.error("New password must be different from current password")
                    return
                
                # Attempt password change
                ip_address = self._get_client_ip()
                session_id = st.session_state.get('session_id', 'unknown')
                
                success = self.db_manager.change_password(
                    username=current_user['username'],
                    old_password=current_password,
                    new_password=new_password,
                    ip_address=ip_address,
                    session_id=session_id
                )
                
                if success:
                    st.success("Password changed successfully!")
                    st.session_state.show_change_password = False
                    
                    # Force re-authentication for security
                    self.db_manager.log_audit_event(
                        user_id=current_user['id'],
                        username=current_user['username'],
                        action_type="PASSWORD_CHANGE_REAUTHENTICATION",
                        resource="user_account",
                        status="initiated",
                        details="Forcing re-authentication after password change for security",
                        ip_address=ip_address,
                        session_id=session_id,
                        severity_level="INFO"
                    )
                    
                    st.info("Please log in again with your new password for security.")
                    self.logout_user()
                else:
                    st.error("Current password is incorrect")
        
        # Password strength guidelines
        with st.expander("Password Security Guidelines"):
            st.markdown("""
            **Strong Password Requirements:**
            - At least 8 characters long
            - Mix of uppercase and lowercase letters
            - Include numbers and special characters
            - Avoid common words or personal information
            - Different from your current password
            - Unique to this system (don't reuse passwords)
            """)
    
    def get_session_info(self) -> Dict[str, Any]:
        """
        Get current session information for audit purposes
        
        Returns:
            Dictionary containing session metadata
        """
        current_user = self.get_current_user()
        login_time = st.session_state.get('login_time', datetime.now())
        if isinstance(login_time, str):
            login_time = datetime.fromisoformat(login_time)
        
        return {
            'session_id': st.session_state.get('session_id', 'unknown'),
            'user_id': current_user['id'] if current_user else None,
            'username': current_user['username'] if current_user else 'anonymous',
            'role': current_user['role'] if current_user else 'none',
            'login_time': login_time.isoformat(),
            'last_activity': st.session_state.get('last_activity', datetime.now()).isoformat(),
            'ip_address': self._get_client_ip(),
            'user_agent': self._get_user_agent(),
            'session_duration': str(datetime.now() - login_time).split('.')[0] if current_user else '0:00:00'
        } 