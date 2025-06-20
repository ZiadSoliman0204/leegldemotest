"""
Database module for Law Firm AI Assistant
Handles user authentication and audit logging with SQLite
"""

import sqlite3
import hashlib
import bcrypt
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations for users and audit logs"""
    
    def __init__(self, db_path: str = "frontend/data/lawfirm_app.db"):
        self.db_path = db_path
        self._ensure_database_directory()
        self._initialize_database()
    
    def _ensure_database_directory(self):
        """Ensure the database directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self):
        """Get database connection with proper configuration"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _initialize_database(self):
        """Initialize database tables if they don't exist"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        hashed_password TEXT NOT NULL,
                        role TEXT DEFAULT 'user',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                """)
                
                # Create audit_log table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        username TEXT,
                        action TEXT NOT NULL,
                        details TEXT,
                        ip_address TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # Create default admin user if no users exist
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                if user_count == 0:
                    self._create_default_admin()
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as error:
            logger.error(f"Error initializing database: {error}")
            raise
    
    def _create_default_admin(self):
        """Create default admin user"""
        default_password = "admin123"  # Should be changed on first login
        hashed_password = self._hash_password(default_password)
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, hashed_password, role)
                    VALUES (?, ?, ?)
                """, ("admin", hashed_password, "admin"))
                conn.commit()
                logger.info("Default admin user created (username: admin, password: admin123)")
        except Exception as error:
            logger.error(f"Error creating default admin: {error}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
        except Exception:
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, hashed_password, role, is_active
                    FROM users 
                    WHERE username = ? AND is_active = 1
                """, (username,))
                
                user_row = cursor.fetchone()
                
                if user_row and self._verify_password(password, user_row['hashed_password']):
                    user_data = {
                        'id': user_row['id'],
                        'username': user_row['username'],
                        'role': user_row['role']
                    }
                    
                    # Log successful login
                    self.log_user_action(
                        user_id=user_data['id'],
                        username=username,
                        action="LOGIN_SUCCESS",
                        details="User successfully logged in"
                    )
                    
                    return user_data
                else:
                    # Log failed login attempt
                    self.log_user_action(
                        user_id=None,
                        username=username,
                        action="LOGIN_FAILED",
                        details="Invalid username or password"
                    )
                    return None
                    
        except Exception as error:
            logger.error(f"Authentication error: {error}")
            return None
    
    def log_user_action(self, user_id: Optional[int], username: str, action: str, 
                       details: str = "", ip_address: str = ""):
        """Log user action to audit trail"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_log (user_id, username, action, details, ip_address)
                    VALUES (?, ?, ?, ?, ?)
                """, (user_id, username, action, details, ip_address))
                conn.commit()
                
        except Exception as error:
            logger.error(f"Error logging user action: {error}")
    
    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """Change user password"""
        try:
            # First verify current password
            user = self.authenticate_user(username, old_password)
            if not user:
                return False
            
            # Hash new password
            new_hashed_password = self._hash_password(new_password)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE users 
                    SET hashed_password = ?
                    WHERE username = ?
                """, (new_hashed_password, username))
                conn.commit()
                
                # Log password change
                self.log_user_action(
                    user_id=user['id'],
                    username=username,
                    action="PASSWORD_CHANGED",
                    details="User changed their password"
                )
                
                return True
                
        except Exception as error:
            logger.error(f"Error changing password: {error}")
            return False
    
    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit logs"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT username, action, details, ip_address, timestamp
                    FROM audit_log
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,))
                
                logs = []
                for row in cursor.fetchall():
                    logs.append({
                        'username': row['username'],
                        'action': row['action'],
                        'details': row['details'],
                        'ip_address': row['ip_address'],
                        'timestamp': row['timestamp']
                    })
                
                return logs
                
        except Exception as error:
            logger.error(f"Error retrieving audit logs: {error}")
            return []
    
    def create_user(self, username: str, password: str, role: str = "user") -> bool:
        """
        Create a new user
        
        Args:
            username: Unique username
            password: Plain text password
            role: User role (admin, user)
            
        Returns:
            True if user created successfully, False otherwise
        """
        try:
            hashed_password = self._hash_password(password)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, hashed_password, role)
                    VALUES (?, ?, ?)
                """, (username, hashed_password, role))
                conn.commit()
                
                # Log user creation
                self.log_user_action(
                    user_id=None,
                    username="system",
                    action="USER_CREATED",
                    details=f"New user created: {username} with role: {role}"
                )
                
                return True
                
        except sqlite3.IntegrityError:
            logger.warning(f"User creation failed: Username {username} already exists")
            return False
        except Exception as error:
            logger.error(f"Error creating user: {error}")
            return False
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all active users (for admin purposes)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, username, role, created_at, is_active
                    FROM users
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                """)
                
                users = []
                for row in cursor.fetchall():
                    users.append({
                        'id': row['id'],
                        'username': row['username'],
                        'role': row['role'],
                        'created_at': row['created_at'],
                        'is_active': row['is_active']
                    })
                
                return users
                
        except Exception as error:
            logger.error(f"Error retrieving users: {error}")
            return [] 