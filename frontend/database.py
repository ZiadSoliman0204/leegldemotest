"""
Database module for Law Firm AI Assistant
Handles user authentication and comprehensive audit logging with SQLite
"""

import sqlite3
import hashlib
import bcrypt
import json
import ipaddress
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple
from pathlib import Path
import logging
from cryptography.fernet import Fernet
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages SQLite database operations for users and comprehensive audit logs"""
    
    def __init__(self, db_path: str = "frontend/data/lawfirm_app.db"):
        self.db_path = db_path
        self._encryption_key = self._get_or_create_encryption_key()
        self._cipher = Fernet(self._encryption_key)
        self._ensure_database_directory()
        self._initialize_database()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for sensitive data"""
        key_file = "frontend/data/.audit_key"
        try:
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    return f.read()
            else:
                key = Fernet.generate_key()
                os.makedirs(os.path.dirname(key_file), exist_ok=True)
                with open(key_file, 'wb') as f:
                    f.write(key)
                return key
        except Exception as e:
            logger.warning(f"Could not manage encryption key: {e}")
            return Fernet.generate_key()
    
    def _encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data like IP addresses"""
        try:
            return self._cipher.encrypt(data.encode()).decode()
        except Exception:
            return data  # Fallback to unencrypted if encryption fails
    
    def _decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            return self._cipher.decrypt(encrypted_data.encode()).decode()
        except Exception:
            return encrypted_data  # Return as-is if decryption fails
    
    def _anonymize_ip(self, ip_address: str) -> str:
        """Anonymize IP address for compliance (GDPR/CCPA)"""
        try:
            ip = ipaddress.ip_address(ip_address)
            if ip.version == 4:
                # Zero out last octet for IPv4
                return str(ipaddress.IPv4Address(int(ip) & 0xFFFFFF00))
            else:
                # Zero out last 64 bits for IPv6
                return str(ipaddress.IPv6Address(int(ip) & (0xFFFFFFFFFFFFFFFF << 64)))
        except Exception:
            return "unknown"
    
    def _hash_content(self, content: str) -> str:
        """Create SHA-256 hash of sensitive content"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]  # First 16 chars for audit trail
    
    def _ensure_database_directory(self):
        """Ensure the database directory exists"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self):
        """Get database connection with proper configuration"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _ensure_database_schema(self):
        """Ensure database schema is up to date by adding missing columns"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if last_login column exists
                cursor.execute("PRAGMA table_info(users)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # Add missing columns if they don't exist
                if 'last_login' not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
                    logger.info("Added last_login column to users table")
                
                if 'failed_login_attempts' not in columns:
                    cursor.execute("ALTER TABLE users ADD COLUMN failed_login_attempts INTEGER DEFAULT 0")
                    logger.info("Added failed_login_attempts column to users table")
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error ensuring database schema: {e}")
    
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
                        is_active BOOLEAN DEFAULT 1,
                        last_login TIMESTAMP,
                        failed_login_attempts INTEGER DEFAULT 0
                    )
                """)
                
                # Enhanced audit_logs table (production-grade)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_id INTEGER,
                        username TEXT,
                        ip_address TEXT,
                        action_type TEXT NOT NULL,
                        resource TEXT,
                        status TEXT DEFAULT 'success',
                        details TEXT,
                        severity_level TEXT DEFAULT 'INFO',
                        content_hash TEXT,
                        session_id TEXT,
                        user_agent TEXT,
                        request_id TEXT,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_action_type ON audit_logs(action_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_status ON audit_logs(status)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_username ON audit_logs(username)")
                
                # Migrate old audit_log table if it exists
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='audit_log'")
                if cursor.fetchone():
                    self._migrate_old_audit_table(cursor)
                
                # Create default admin user if no users exist
                cursor.execute("SELECT COUNT(*) FROM users")
                user_count = cursor.fetchone()[0]
                
                if user_count == 0:
                    self._create_default_admin()
                
                conn.commit()
                logger.info("Database initialized successfully")
                
                # Ensure schema is up to date
                self._ensure_database_schema()
                
                # Start automatic cleanup
                self._cleanup_old_logs()
                
        except Exception as error:
            logger.error(f"Error initializing database: {error}")
            raise
    
    def _migrate_old_audit_table(self, cursor):
        """Migrate data from old audit_log table to new audit_logs table"""
        try:
            cursor.execute("SELECT * FROM audit_log")
            old_logs = cursor.fetchall()
            
            for log in old_logs:
                # Use dictionary-style access for SQLite Row objects
                user_id = log['user_id'] if 'user_id' in log.keys() else None
                username = log['username'] if 'username' in log.keys() else None
                action = log['action'] if 'action' in log.keys() else 'UNKNOWN'
                details = log['details'] if 'details' in log.keys() else None
                ip_address = log['ip_address'] if 'ip_address' in log.keys() else None
                timestamp = log['timestamp'] if 'timestamp' in log.keys() else None
                
                cursor.execute("""
                    INSERT INTO audit_logs (user_id, username, action_type, details, ip_address, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (user_id, username, action, details, ip_address, timestamp))
            
            # Drop old table
            cursor.execute("DROP TABLE audit_log")
            logger.info(f"Migrated {len(old_logs)} entries from old audit_log table")
            
        except Exception as e:
            logger.warning(f"Could not migrate old audit table: {e}")
    
    def _cleanup_old_logs(self):
        """Clean up audit logs older than 90 days"""
        try:
            cutoff_date = datetime.now() - timedelta(days=90)
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM audit_logs WHERE timestamp < ?", (cutoff_date,))
                deleted_count = cursor.rowcount
                conn.commit()
                if deleted_count > 0:
                    logger.info(f"Cleaned up {deleted_count} old audit log entries")
        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
    
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
    
    def authenticate_user(self, username: str, password: str, ip_address: str = "", 
                         user_agent: str = "", session_id: str = "") -> Optional[Dict[str, Any]]:
        """Authenticate user with enhanced audit logging"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if the required columns exist
                cursor.execute("PRAGMA table_info(users)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # Build query based on available columns
                select_columns = ['id', 'username', 'hashed_password', 'role', 'is_active']
                if 'failed_login_attempts' in columns:
                    select_columns.append('failed_login_attempts')
                
                query = f"""
                    SELECT {', '.join(select_columns)}
                    FROM users 
                    WHERE username = ? AND is_active = 1
                """
                
                cursor.execute(query, (username,))
                user_row = cursor.fetchone()
                
                if user_row and self._verify_password(password, user_row['hashed_password']):
                    user_data = {
                        'id': user_row['id'],
                        'username': user_row['username'],
                        'role': user_row['role']
                    }
                    
                    # Build update query based on available columns
                    update_parts = []
                    update_params = []
                    
                    if 'failed_login_attempts' in columns:
                        update_parts.append('failed_login_attempts = 0')
                    if 'last_login' in columns:
                        update_parts.append('last_login = CURRENT_TIMESTAMP')
                    
                    if update_parts:
                        update_query = f"""
                            UPDATE users 
                            SET {', '.join(update_parts)}
                            WHERE id = ?
                        """
                        cursor.execute(update_query, (user_data['id'],))
                    
                    # Log successful login
                    self.log_audit_event(
                        user_id=user_data['id'],
                        username=username,
                        action_type="LOGIN_SUCCESS",
                        resource="authentication",
                        status="success",
                        details="User successfully authenticated",
                        ip_address=ip_address,
                        user_agent=user_agent,
                        session_id=session_id,
                        severity_level="INFO"
                    )
                    
                    return user_data
                else:
                    # Increment failed login attempts if column exists
                    if user_row and 'failed_login_attempts' in columns:
                        current_attempts = user_row['failed_login_attempts'] or 0
                        new_attempts = current_attempts + 1
                        cursor.execute("""
                            UPDATE users 
                            SET failed_login_attempts = ?
                            WHERE username = ?
                        """, (new_attempts, username))
                    
                    # Log failed login attempt
                    self.log_audit_event(
                        user_id=user_row['id'] if user_row else None,
                        username=username,
                        action_type="LOGIN_FAILED",
                        resource="authentication",
                        status="failure",
                        details="Invalid username or password",
                        ip_address=ip_address,
                        user_agent=user_agent,
                        session_id=session_id,
                        severity_level="WARNING"
                    )
                    return None
                    
        except Exception as error:
            logger.error(f"Authentication error: {error}")
            # Log authentication error
            self.log_audit_event(
                user_id=None,
                username=username,
                action_type="AUTH_ERROR",
                resource="authentication",
                status="error",
                details=f"Authentication system error: {str(error)}",
                ip_address=ip_address,
                severity_level="ERROR"
            )
            return None
    
    def log_audit_event(self, user_id: Optional[int], username: str, action_type: str,
                       resource: str = "", status: str = "success", details: str = "",
                       ip_address: str = "", user_agent: str = "", session_id: str = "",
                       request_id: str = "", severity_level: str = "INFO", 
                       content_to_hash: str = ""):
        """
        Enhanced audit event logging with security features
        
        Args:
            user_id: User ID (nullable for anonymous actions)
            username: Username for quick lookup
            action_type: Type of action (LOGIN, DOC_UPLOAD, CHAT, etc.)
            resource: Resource affected (filename, doc ID, etc.)
            status: success/failure/error
            details: Additional details (JSON string or plain text)
            ip_address: Client IP address (will be encrypted/anonymized)
            user_agent: Browser/client user agent
            session_id: Session identifier
            request_id: Request correlation ID
            severity_level: INFO/WARNING/ERROR
            content_to_hash: Sensitive content to hash (prompts, etc.)
        """
        try:
            # Process IP address (encrypt or anonymize based on configuration)
            processed_ip = self._anonymize_ip(ip_address) if ip_address else ""
            
            # Hash sensitive content if provided
            content_hash = self._hash_content(content_to_hash) if content_to_hash else ""
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO audit_logs (
                        user_id, username, action_type, resource, status, details,
                        ip_address, user_agent, session_id, request_id, 
                        severity_level, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    user_id, username, action_type, resource, status, details,
                    processed_ip, user_agent, session_id, request_id, 
                    severity_level, content_hash
                ))
                conn.commit()
                
        except Exception as error:
            logger.error(f"Error logging audit event: {error}")
    
    def log_user_action(self, user_id: Optional[int], username: str, action: str, 
                       details: str = "", ip_address: str = ""):
        """Legacy method for backward compatibility"""
        self.log_audit_event(
            user_id=user_id,
            username=username,
            action_type=action,
            details=details,
            ip_address=ip_address
        )
    
    def get_audit_logs_filtered(self, page: int = 1, page_size: int = 50,
                               action_type: str = "", username: str = "",
                               status: str = "", severity_level: str = "",
                               date_from: str = "", date_to: str = "",
                               user_role: str = "admin") -> Tuple[List[Dict[str, Any]], int]:
        """
        Get filtered audit logs with pagination
        
        Returns:
            Tuple of (logs_list, total_count)
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Build WHERE clause dynamically
                where_conditions = []
                params = []
                
                if action_type:
                    where_conditions.append("action_type LIKE ?")
                    params.append(f"%{action_type}%")
                
                if username:
                    where_conditions.append("username LIKE ?")
                    params.append(f"%{username}%")
                
                if status:
                    where_conditions.append("status = ?")
                    params.append(status)
                
                if severity_level:
                    where_conditions.append("severity_level = ?")
                    params.append(severity_level)
                
                if date_from:
                    where_conditions.append("DATE(timestamp) >= ?")
                    params.append(date_from)
                
                if date_to:
                    where_conditions.append("DATE(timestamp) <= ?")
                    params.append(date_to)
                
                where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
                
                # Get total count
                count_query = f"SELECT COUNT(*) FROM audit_logs WHERE {where_clause}"
                cursor.execute(count_query, params)
                total_count = cursor.fetchone()[0]
                
                # Get paginated results
                offset = (page - 1) * page_size
                query = f"""
                    SELECT id, timestamp, user_id, username, ip_address, action_type,
                           resource, status, details, severity_level, content_hash,
                           session_id, user_agent, request_id
                    FROM audit_logs 
                    WHERE {where_clause}
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                """
                
                cursor.execute(query, params + [page_size, offset])
                
                logs = []
                for row in cursor.fetchall():
                    logs.append({
                        'id': row['id'],
                        'timestamp': row['timestamp'],
                        'user_id': row['user_id'],
                        'username': row['username'],
                        'ip_address': row['ip_address'],
                        'action_type': row['action_type'],
                        'resource': row['resource'],
                        'status': row['status'],
                        'details': row['details'],
                        'severity_level': row['severity_level'],
                        'content_hash': row['content_hash'],
                        'session_id': row['session_id'],
                        'user_agent': row['user_agent'],
                        'request_id': row['request_id']
                    })
                
                return logs, total_count
                
        except Exception as error:
            logger.error(f"Error retrieving filtered audit logs: {error}")
            return [], 0
    
    def get_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit logs (legacy method for backward compatibility)"""
        logs, _ = self.get_audit_logs_filtered(page=1, page_size=limit)
        return logs
    
    def export_audit_logs_csv(self, filters: Dict[str, str] = None) -> str:
        """Export audit logs to CSV format"""
        import csv
        import io
        
        try:
            filters = filters or {}
            logs, _ = self.get_audit_logs_filtered(
                page=1, 
                page_size=10000,  # Large limit for export
                **filters
            )
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'ID', 'Timestamp', 'Username', 'Action Type', 'Resource', 
                'Status', 'IP Address', 'Severity Level', 'Content Hash', 'Details'
            ])
            
            # Write data
            for log in logs:
                writer.writerow([
                    log['id'], log['timestamp'], log['username'], log['action_type'],
                    log['resource'], log['status'], log['ip_address'], 
                    log['severity_level'], log['content_hash'], log['details']
                ])
            
            return output.getvalue()
            
        except Exception as error:
            logger.error(f"Error exporting audit logs: {error}")
            return ""
    
    def change_password(self, username: str, old_password: str, new_password: str, 
                       ip_address: str = "", session_id: str = "") -> bool:
        """Change user password with enhanced audit logging"""
        try:
            # First verify current password
            user = self.authenticate_user(username, old_password, ip_address)
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
                self.log_audit_event(
                    user_id=user['id'],
                    username=username,
                    action_type="PASSWORD_CHANGED",
                    resource="user_account",
                    status="success",
                    details="User successfully changed password",
                    ip_address=ip_address,
                    session_id=session_id,
                    severity_level="INFO"
                )
                
                return True
                
        except Exception as error:
            logger.error(f"Error changing password: {error}")
            self.log_audit_event(
                user_id=None,
                username=username,
                action_type="PASSWORD_CHANGE_ERROR",
                resource="user_account",
                status="error",
                details=f"Password change failed: {str(error)}",
                ip_address=ip_address,
                severity_level="ERROR"
            )
            return False
    
    def create_user(self, username: str, password: str, role: str = "user", 
                   creator_username: str = "system", ip_address: str = "") -> bool:
        """Create a new user with enhanced audit logging"""
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
                self.log_audit_event(
                    user_id=None,
                    username=creator_username,
                    action_type="USER_CREATED",
                    resource=f"user:{username}",
                    status="success",
                    details=f"New user created: {username} with role: {role}",
                    ip_address=ip_address,
                    severity_level="INFO"
                )
                
                return True
                
        except sqlite3.IntegrityError:
            logger.warning(f"User creation failed: Username {username} already exists")
            self.log_audit_event(
                user_id=None,
                username=creator_username,
                action_type="USER_CREATE_FAILED",
                resource=f"user:{username}",
                status="failure",
                details=f"User creation failed: Username already exists",
                ip_address=ip_address,
                severity_level="WARNING"
            )
            return False
        except Exception as error:
            logger.error(f"Error creating user: {error}")
            self.log_audit_event(
                user_id=None,
                username=creator_username,
                action_type="USER_CREATE_ERROR",
                resource=f"user:{username}",
                status="error",
                details=f"User creation error: {str(error)}",
                ip_address=ip_address,
                severity_level="ERROR"
            )
            return False
    
    def get_users(self) -> List[Dict[str, Any]]:
        """Get all active users (for admin purposes)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # First check if the required columns exist
                cursor.execute("PRAGMA table_info(users)")
                columns = [column[1] for column in cursor.fetchall()]
                
                # Build query based on available columns
                select_columns = ['id', 'username', 'role', 'created_at', 'is_active']
                if 'last_login' in columns:
                    select_columns.append('last_login')
                if 'failed_login_attempts' in columns:
                    select_columns.append('failed_login_attempts')
                
                query = f"""
                    SELECT {', '.join(select_columns)}
                    FROM users
                    WHERE is_active = 1
                    ORDER BY created_at DESC
                """
                
                cursor.execute(query)
                
                users = []
                for row in cursor.fetchall():
                    user_data = {
                        'id': row['id'],
                        'username': row['username'],
                        'role': row['role'],
                        'created_at': row['created_at'],
                        'is_active': row['is_active']
                    }
                    
                    # Add optional columns if they exist
                    if 'last_login' in columns:
                        user_data['last_login'] = row['last_login']
                    if 'failed_login_attempts' in columns:
                        user_data['failed_login_attempts'] = row['failed_login_attempts']
                    
                    users.append(user_data)
                
                return users
                
        except Exception as error:
            logger.error(f"Error retrieving users: {error}")
            return [] 