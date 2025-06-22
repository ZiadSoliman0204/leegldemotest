"""
Production-grade Streamlit Frontend for Law Firm AI Assistant
Features: Authentication, themes, document management, analytics
"""

import streamlit as st
import requests
import os
import uuid
import hashlib
from datetime import datetime, date
from typing import Optional, Dict, Any, List
import json

# Import our custom modules
try:
    from auth import AuthManager
    from theme import ThemeManager
    from database import DatabaseManager
except ImportError:
    # Fallback for development
    import sys
    import os
    current_dir = os.path.dirname(__file__)
    if current_dir:
        sys.path.append(current_dir)
    else:
        sys.path.append('frontend')
    from auth import AuthManager
    from theme import ThemeManager
    from database import DatabaseManager

# Configuration Constants
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
DEFAULT_TIMEOUT = 60
UPLOAD_TIMEOUT = 120
DEFAULT_MAX_TOKENS = 2048
DEFAULT_TEMPERATURE = 0.7

class LawFirmAIApp:
    """Main application class for Law Firm AI Assistant"""
    
    def __init__(self):
        self.auth_manager = AuthManager()
        self.theme_manager = ThemeManager()
        self.db_manager = DatabaseManager()
        self.session_id = self._get_or_create_session_id()
        self._initialize_session_state()
    
    def _get_or_create_session_id(self) -> str:
        """Get or create session ID for audit tracking"""
        if 'session_id' not in st.session_state:
            st.session_state.session_id = str(uuid.uuid4())
        return st.session_state.session_id
    
    def _get_client_ip(self) -> str:
        """Get client IP address from request headers"""
        try:
            # Try to get real IP from headers (works with reverse proxies)
            if 'X-Forwarded-For' in st.context.headers:
                return st.context.headers['X-Forwarded-For'].split(',')[0].strip()
            elif 'X-Real-IP' in st.context.headers:
                return st.context.headers['X-Real-IP']
            else:
                return "127.0.0.1"  # Fallback for local development
        except Exception:
            return "unknown"
    
    def _get_user_agent(self) -> str:
        """Get user agent from request headers"""
        try:
            return st.context.headers.get('User-Agent', 'unknown')
        except Exception:
            return "unknown"
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        default_values = {
            'messages': [],
            'documents_uploaded': [],
            'api_status': 'unknown',
            'current_view': 'chat',
            'use_rag': True,
            'max_tokens': DEFAULT_MAX_TOKENS,
            'temperature': DEFAULT_TEMPERATURE,
            'show_change_password': False,
            # Chat history variables
            'current_chat_session_id': None,
            'chat_sessions': [],
            'chat_sessions_loaded': False,
            'chat_history_needs_refresh': False
        }
        
        for key, value in default_values.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def check_api_health(self):
        """Check if the backend API is running"""
        try:
            response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            if response.status_code == 200:
                st.session_state.api_status = "online"
            else:
                st.session_state.api_status = "offline"
        except Exception:
            st.session_state.api_status = "offline"
    
    def render_header(self):
        """Render application header"""
        st.markdown("""
        <div class="main-header">
            <h1>Legal AI Assistant</h1>
            <p>Professional AI-powered legal research and document analysis</p>
        </div>
        """, unsafe_allow_html=True)
    
    def render_api_status(self):
        """Render API connection status"""
        if st.session_state.api_status == "online":
            self.theme_manager.render_status_indicator("online", "API Connected")
        else:
            self.theme_manager.render_status_indicator("offline", "API Disconnected")
    
    def render_navigation(self):
        """Render navigation menu with chat history"""
        with st.sidebar:
            # Chat History Section
            self.render_chat_history_sidebar()
            
            st.markdown("---")
            st.header("Navigation")
            
            # Basic views for all users
            views = {
                'chat': 'Chat Assistant',
                'documents': 'Document Management',
                'analytics': 'Analytics Dashboard'
            }
            
            # Add admin-only views
            current_user = self.auth_manager.get_current_user()
            if current_user and current_user.get('role') == 'admin':
                views.update({
                    'audit': 'Audit Logs',
                    'users': 'User Management'
                })
            
            for view_key, view_name in views.items():
                if st.button(view_name, use_container_width=True):
                    st.session_state.current_view = view_key
                    st.rerun()
    
    def render_chat_history_sidebar(self):
        """Render chat history in sidebar"""
        current_user = self.auth_manager.get_current_user()
        if not current_user:
            return
        
        st.header("Chat History")
        
        # Load chat sessions if not already loaded
        if not st.session_state.chat_sessions_loaded or st.session_state.chat_history_needs_refresh:
            st.session_state.chat_sessions = self.db_manager.get_user_chat_sessions(current_user['id'])
            st.session_state.chat_sessions_loaded = True
            st.session_state.chat_history_needs_refresh = False
        
        # New Chat button
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("New Chat", use_container_width=True, type="primary"):
                self.start_new_chat()
        
        with col2:
            if st.button("Refresh", help="Refresh chat list"):
                st.session_state.chat_history_needs_refresh = True
                st.rerun()
        
        # Current session indicator
        if st.session_state.current_chat_session_id:
            current_session = self.db_manager.get_chat_session_info(
                st.session_state.current_chat_session_id, 
                current_user['id']
            )
            if current_session:
                st.info(f"**Current:** {current_session['title']}")
        
        # Chat sessions list
        if st.session_state.chat_sessions:
            st.markdown("**Recent Chats:**")
            
            for session in st.session_state.chat_sessions[:10]:  # Show last 10 chats
                # Format timestamp
                try:
                    from datetime import datetime
                    created_time = datetime.fromisoformat(session['created_at'])
                    time_str = created_time.strftime("%m/%d %H:%M")
                except:
                    time_str = "Unknown"
                
                # Chat item container
                with st.container():
                    col_title, col_action = st.columns([4, 1])
                    
                    with col_title:
                        # Truncate long titles
                        title = session['title']
                        if len(title) > 25:
                            title = title[:22] + "..."
                        
                        # Different style for current session
                        if session['id'] == st.session_state.current_chat_session_id:
                            st.markdown(f"**• {title}**")
                        else:
                            if st.button(f"{title}", key=f"chat_{session['id']}", use_container_width=True):
                                self.load_chat_session(session['id'])
                        
                        st.caption(f"{time_str} • {session['message_count']} msgs")
                    
                    with col_action:
                        # Delete button
                        if st.button("Delete", key=f"del_{session['id']}", help="Delete chat"):
                            if self.delete_chat_session(session['id']):
                                st.rerun()
                
                st.markdown("---")
        else:
            st.info("No previous chats. Start a new conversation!")
    
    def render_settings_sidebar(self):
        """Render settings in sidebar"""
        with st.sidebar:
            st.header("Settings")
            
            # RAG settings
            use_rag = st.checkbox(
                "Use Document Context", 
                value=st.session_state.use_rag,
                help="Enable RAG to use uploaded documents for context"
            )
            st.session_state.use_rag = use_rag
            
            # Token settings
            max_tokens = st.slider(
                "Max Response Tokens", 
                100, 4000, 
                st.session_state.max_tokens
            )
            st.session_state.max_tokens = max_tokens
            
            # Temperature settings
            temperature = st.slider(
                "Response Creativity", 
                0.0, 1.0, 
                st.session_state.temperature, 
                0.1
            )
            st.session_state.temperature = temperature
    
    # Chat History Management Methods
    
    def start_new_chat(self):
        """Start a new chat session"""
        current_user = self.auth_manager.get_current_user()
        if not current_user:
            st.error("Please log in to start a new chat")
            return
        
        # Create new session in database
        session_id = self.db_manager.create_chat_session(current_user['id'])
        
        if session_id:
            # Clear current messages and set new session
            st.session_state.messages = []
            st.session_state.current_chat_session_id = session_id
            st.session_state.chat_history_needs_refresh = True
            
            # Log the new chat session
            self.db_manager.log_audit_event(
                user_id=current_user['id'],
                username=current_user['username'],
                action_type="CHAT_SESSION_CREATED",
                resource=f"chat_session:{session_id}",
                status="success",
                details="New chat session created",
                ip_address=self._get_client_ip(),
                session_id=self.session_id,
                severity_level="INFO"
            )
            
            st.success("New chat started!")
            st.rerun()
        else:
            st.error("Failed to create new chat session")
    
    def load_chat_session(self, session_id: int):
        """Load an existing chat session"""
        current_user = self.auth_manager.get_current_user()
        if not current_user:
            return
        
        # Load messages from database
        messages = self.db_manager.get_chat_messages(session_id, current_user['id'])
        
        if messages is not None:  # None means unauthorized access
            # Convert database messages to session state format
            st.session_state.messages = []
            for msg in messages:
                st.session_state.messages.append({
                    'role': msg['role'],
                    'content': msg['content'],
                    'sources': msg.get('sources', [])
                })
            
            st.session_state.current_chat_session_id = session_id
            
            # Log session access
            self.db_manager.log_audit_event(
                user_id=current_user['id'],
                username=current_user['username'],
                action_type="CHAT_SESSION_LOADED",
                resource=f"chat_session:{session_id}",
                status="success",
                details=f"Loaded chat session with {len(messages)} messages",
                ip_address=self._get_client_ip(),
                session_id=self.session_id,
                severity_level="INFO"
            )
            
            st.rerun()
        else:
            st.error("Unable to load chat session")
    
    def delete_chat_session(self, session_id: int) -> bool:
        """Delete a chat session"""
        current_user = self.auth_manager.get_current_user()
        if not current_user:
            return False
        
        # Delete from database
        success = self.db_manager.delete_chat_session(session_id, current_user['id'])
        
        if success:
            # If current session was deleted, clear it
            if st.session_state.current_chat_session_id == session_id:
                st.session_state.current_chat_session_id = None
                st.session_state.messages = []
            
            # Refresh chat list
            st.session_state.chat_history_needs_refresh = True
            
            st.success("Chat deleted successfully")
            return True
        else:
            st.error("Failed to delete chat")
            return False
    
    def save_message_to_current_session(self, role: str, content: str, sources: List[str] = None):
        """Save a message to the current chat session"""
        current_user = self.auth_manager.get_current_user()
        if not current_user:
            return
        
        # Ensure we have a current session
        if not st.session_state.current_chat_session_id:
            # Create a new session if none exists
            session_id = self.db_manager.create_chat_session(current_user['id'])
            if session_id:
                st.session_state.current_chat_session_id = session_id
                st.session_state.chat_history_needs_refresh = True
            else:
                st.error("Failed to create chat session")
                return
        
        # Save message to database
        success = self.db_manager.add_chat_message(
            session_id=st.session_state.current_chat_session_id,
            user_id=current_user['id'],
            role=role,
            content=content,
            sources=sources
        )
        
        if success:
            # Refresh chat sessions to update message count
            st.session_state.chat_history_needs_refresh = True
        else:
            st.warning("Message saved to session but not persisted to database")
    
    def export_current_chat(self):
        """Export current chat to text format"""
        if not st.session_state.messages:
            st.warning("No messages to export")
            return
        
        current_user = self.auth_manager.get_current_user()
        if not current_user:
            return
        
        # Get session info for title
        session_title = "Untitled Chat"
        if st.session_state.current_chat_session_id:
            session_info = self.db_manager.get_chat_session_info(
                st.session_state.current_chat_session_id, 
                current_user['id']
            )
            if session_info:
                session_title = session_info['title']
        
        # Generate export content
        export_content = f"Chat Export: {session_title}\n"
        export_content += f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        export_content += f"User: {current_user['username']}\n"
        export_content += "=" * 50 + "\n\n"
        
        for msg in st.session_state.messages:
            role = "You" if msg['role'] == 'user' else "Legal Assistant"
            export_content += f"{role}:\n{msg['content']}\n\n"
            
            if msg.get('sources'):
                export_content += "Sources:\n"
                for i, source in enumerate(msg['sources'], 1):
                    export_content += f"  {i}. {source}\n"
                export_content += "\n"
            
            export_content += "-" * 30 + "\n\n"
        
        # Provide download
        st.download_button(
            label="Download as .txt",
            data=export_content.encode('utf-8'),
            file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
        
        # Log export action
        self.db_manager.log_audit_event(
            user_id=current_user['id'],
            username=current_user['username'],
            action_type="CHAT_EXPORT",
            resource=f"chat_session:{st.session_state.current_chat_session_id}",
            status="success",
            details=f"Exported chat '{session_title}' with {len(st.session_state.messages)} messages",
            ip_address=self._get_client_ip(),
            session_id=self.session_id,
            severity_level="INFO"
        )
    
    def send_chat_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Send a chat message to the API with enhanced audit logging"""
        current_user = self.auth_manager.get_current_user()
        ip_address = self._get_client_ip()
        user_agent = self._get_user_agent()
        
        # Log chat initiation
        self.db_manager.log_audit_event(
            user_id=current_user['id'] if current_user else None,
            username=current_user['username'] if current_user else 'anonymous',
            action_type="CHAT_INITIATED",
            resource="chat_completion",
            status="initiated",
            details=f"Chat message length: {len(message)} characters",
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=self.session_id,
            content_to_hash=message,  # Hash the prompt for audit
            severity_level="INFO"
        )
        
        try:
            payload = self._build_chat_payload(message)
            response = self._make_api_request(payload)
            
            if response.status_code == 200:
                result = response.json()
                
                # Log successful chat completion
                self.db_manager.log_audit_event(
                    user_id=current_user['id'] if current_user else None,
                    username=current_user['username'] if current_user else 'anonymous',
                    action_type="CHAT_COMPLETED",
                    resource="chat_completion",
                    status="success",
                    details=f"Response generated successfully. Tokens used: {result.get('usage', {}).get('total_tokens', 'unknown')}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=self.session_id,
                    severity_level="INFO"
                )
                
                return result
            else:
                # Log API error
                self.db_manager.log_audit_event(
                    user_id=current_user['id'] if current_user else None,
                    username=current_user['username'] if current_user else 'anonymous',
                    action_type="CHAT_API_ERROR",
                    resource="chat_completion",
                    status="error",
                    details=f"API Error: {response.status_code} - {response.text}",
                    ip_address=ip_address,
                    session_id=self.session_id,
                    severity_level="ERROR"
                )
                
                st.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as error:
            # Log connection error
            self.db_manager.log_audit_event(
                user_id=current_user['id'] if current_user else None,
                username=current_user['username'] if current_user else 'anonymous',
                action_type="CHAT_CONNECTION_ERROR",
                resource="chat_completion",
                status="error",
                details=f"Connection error: {str(error)}",
                ip_address=ip_address,
                session_id=self.session_id,
                severity_level="ERROR"
            )
            
            st.error(f"Connection error: {str(error)}")
            return None
        except Exception as error:
            # Log unexpected error
            self.db_manager.log_audit_event(
                user_id=current_user['id'] if current_user else None,
                username=current_user['username'] if current_user else 'anonymous',
                action_type="CHAT_SYSTEM_ERROR",
                resource="chat_completion",
                status="error",
                details=f"System error: {str(error)}",
                ip_address=ip_address,
                session_id=self.session_id,
                severity_level="ERROR"
            )
            
            st.error(f"Unexpected error: {str(error)}")
            return None
    
    def _build_chat_payload(self, message: str) -> Dict[str, Any]:
        """Build the payload for chat API request"""
        return {
            "message": message,
            "use_rag": st.session_state.use_rag,
            "max_tokens": st.session_state.max_tokens,
            "temperature": st.session_state.temperature
        }
    
    def _make_api_request(self, payload: Dict[str, Any]) -> requests.Response:
        """Make the actual API request"""
        return requests.post(
            f"{API_BASE_URL}/api/v1/chat/completions",
            json=payload,
            timeout=DEFAULT_TIMEOUT
        )
    
    def render_chat_messages(self):
        """Render chat message history"""
        for message in st.session_state.messages:
            if message["role"] == "user":
                self._render_user_message(message["content"])
            else:
                self._render_assistant_message(message["content"])
                
                # Show sources if available
                if "sources" in message and message["sources"]:
                    self._render_sources(message["sources"])
    
    def _render_user_message(self, content: str):
        """Render a user message"""
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>User:</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)
    
    def _render_assistant_message(self, content: str):
        """Render an assistant message"""
        st.markdown(f"""
        <div class="chat-message assistant-message">
            <strong>Legal Assistant:</strong><br>
            {content}
        </div>
        """, unsafe_allow_html=True)
    
    def _render_sources(self, sources: List[str]):
        """Render document sources"""
        with st.expander("View Sources"):
            for i, source in enumerate(sources, 1):
                st.markdown(f"**Source {i}:** {source}")
    
    def handle_chat_input(self):
        """Handle chat input and processing"""
        user_input = st.chat_input("Ask your legal question here...")
        
        if user_input:
            self._process_user_input(user_input)
    
    def _process_user_input(self, user_input: str):
        """Process user input and get AI response"""
        # Add user message to history
        self._add_message_to_history("user", user_input)
        
        # Log user action
        self.auth_manager.log_user_action("CHAT_MESSAGE", f"User sent message: {user_input[:100]}...")
        
        # Send to API and get response
        with st.spinner("Thinking..."):
            response = self.send_chat_message(user_input)
            
            if response:
                self._handle_api_response(response)
        
        # Rerun to show new messages
        st.rerun()
    
    def _add_message_to_history(self, role: str, content: str, sources: List[str] = None):
        """Add a message to the chat history and save to database"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if sources:
            message["sources"] = sources
        
        st.session_state.messages.append(message)
        
        # Save to database
        self.save_message_to_current_session(role, content, sources)
    
    def _handle_api_response(self, response: Dict[str, Any]):
        """Handle API response and add to chat history"""
        assistant_content = response.get("response", "Sorry, I couldn't process your request.")
        sources = response.get("sources", [])
        
        self._add_message_to_history("assistant", assistant_content, sources)
        
        # Log successful response
        self.auth_manager.log_user_action("CHAT_RESPONSE", "Received AI response")
    
    def render_chat_interface(self):
        """Render the main chat interface"""
        st.header("Legal Assistant Chat")
        
        # Chat history container
        chat_container = st.container()
        with chat_container:
            if not st.session_state.messages:
                st.info("Start a conversation by asking a legal question below.")
            else:
                self.render_chat_messages()
        
        # Clear chat button
        if st.session_state.messages:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Clear Current Chat", use_container_width=True):
                    st.session_state.messages = []
                    # Start a new session for the next message
                    st.session_state.current_chat_session_id = None
                    self.auth_manager.log_user_action("CHAT_CLEARED", "User cleared current chat")
                    st.rerun()
            
            with col2:
                if st.button("Export Chat", use_container_width=True):
                    self.export_current_chat()
    
    def upload_document(self, uploaded_file):
        """Upload document with enhanced audit logging"""
        current_user = self.auth_manager.get_current_user()
        ip_address = self._get_client_ip()
        user_agent = self._get_user_agent()
        
        if not uploaded_file:
            return
        
        # Log document upload initiation
        self.db_manager.log_audit_event(
            user_id=current_user['id'] if current_user else None,
            username=current_user['username'] if current_user else 'anonymous',
            action_type="DOC_UPLOAD_INITIATED",
            resource=f"document:{uploaded_file.name}",
            status="initiated",
            details=f"File size: {uploaded_file.size} bytes, Type: {uploaded_file.type}",
            ip_address=ip_address,
            user_agent=user_agent,
            session_id=self.session_id,
            severity_level="INFO"
        )
        
        try:
            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            response = requests.post(
                f"{API_BASE_URL}/api/v1/documents/upload",
                files=files,
                timeout=UPLOAD_TIMEOUT
            )
            
            if response.status_code == 200:
                result = response.json()
                st.success(f"Document '{uploaded_file.name}' uploaded successfully!")
                
                # Log successful upload
                self.db_manager.log_audit_event(
                    user_id=current_user['id'] if current_user else None,
                    username=current_user['username'] if current_user else 'anonymous',
                    action_type="DOC_UPLOAD_SUCCESS",
                    resource=f"document:{uploaded_file.name}",
                    status="success",
                    details=f"Document ID: {result.get('document_id', 'unknown')}, Chunks: {result.get('chunk_count', 0)}",
                    ip_address=ip_address,
                    user_agent=user_agent,
                    session_id=self.session_id,
                    severity_level="INFO"
                )
                
                # Log user action for legacy compatibility
                self.auth_manager.log_user_action(
                    "DOCUMENT_UPLOADED", 
                    f"Uploaded document: {uploaded_file.name}"
                )
                
                self.load_document_list()
            else:
                error_msg = f"Upload failed: {response.text}"
                st.error(error_msg)
                
                # Log upload failure
                self.db_manager.log_audit_event(
                    user_id=current_user['id'] if current_user else None,
                    username=current_user['username'] if current_user else 'anonymous',
                    action_type="DOC_UPLOAD_FAILED",
                    resource=f"document:{uploaded_file.name}",
                    status="failure",
                    details=f"Upload failed: {response.status_code} - {response.text}",
                    ip_address=ip_address,
                    session_id=self.session_id,
                    severity_level="WARNING"
                )
                
        except Exception as error:
            error_msg = f"Error uploading document: {str(error)}"
            st.error(error_msg)
            
            # Log upload error
            self.db_manager.log_audit_event(
                user_id=current_user['id'] if current_user else None,
                username=current_user['username'] if current_user else 'anonymous',
                action_type="DOC_UPLOAD_ERROR",
                resource=f"document:{uploaded_file.name}",
                status="error",
                details=f"Upload error: {str(error)}",
                ip_address=ip_address,
                session_id=self.session_id,
                severity_level="ERROR"
            )
    
    def delete_document(self, document_id: str, filename: str):
        """Delete document with enhanced audit logging"""
        current_user = self.auth_manager.get_current_user()
        ip_address = self._get_client_ip()
        
        # Log document deletion attempt
        self.db_manager.log_audit_event(
            user_id=current_user['id'] if current_user else None,
            username=current_user['username'] if current_user else 'anonymous',
            action_type="DOC_DELETE_INITIATED",
            resource=f"document:{filename}",
            status="initiated",
            details=f"Document ID: {document_id}",
            ip_address=ip_address,
            session_id=self.session_id,
            severity_level="INFO"
        )
        
        try:
            response = requests.delete(f"{API_BASE_URL}/api/v1/documents/{document_id}")
            
            if response.status_code == 200:
                st.success(f"Document '{filename}' deleted successfully!")
                
                # Log successful deletion
                self.db_manager.log_audit_event(
                    user_id=current_user['id'] if current_user else None,
                    username=current_user['username'] if current_user else 'anonymous',
                    action_type="DOC_DELETE_SUCCESS",
                    resource=f"document:{filename}",
                    status="success",
                    details=f"Document successfully deleted. ID: {document_id}",
                    ip_address=ip_address,
                    session_id=self.session_id,
                    severity_level="INFO"
                )
                
                # Legacy audit logging
                self.auth_manager.log_user_action(
                    "DOCUMENT_DELETED", 
                    f"Deleted document: {filename}"
                )
                
                self.load_document_list()
            else:
                error_msg = f"Failed to delete document: {response.text}"
                st.error(error_msg)
                
                # Log deletion failure
                self.db_manager.log_audit_event(
                    user_id=current_user['id'] if current_user else None,
                    username=current_user['username'] if current_user else 'anonymous',
                    action_type="DOC_DELETE_FAILED",
                    resource=f"document:{filename}",
                    status="failure",
                    details=f"Deletion failed: {response.status_code} - {response.text}",
                    ip_address=ip_address,
                    session_id=self.session_id,
                    severity_level="WARNING"
                )
                
        except Exception as error:
            error_msg = f"Error deleting document: {str(error)}"
            st.error(error_msg)
            
            # Log deletion error
            self.db_manager.log_audit_event(
                user_id=current_user['id'] if current_user else None,
                username=current_user['username'] if current_user else 'anonymous',
                action_type="DOC_DELETE_ERROR",
                resource=f"document:{filename}",
                status="error",
                details=f"Deletion error: {str(error)}",
                ip_address=ip_address,
                session_id=self.session_id,
                severity_level="ERROR"
            )
    
    def load_document_list(self):
        """Load the list of uploaded documents"""
        try:
            response = requests.get(f"{API_BASE_URL}/api/v1/documents/list")
            if response.status_code == 200:
                result = response.json()
                st.session_state.documents_uploaded = result.get("documents", [])
            else:
                st.error("Failed to load document list")
                
        except Exception as error:
            st.error(f"Error loading documents: {str(error)}")
    
    def render_document_management(self):
        """Render document management interface"""
        st.header("Document Management")
        
        # Upload section
        st.subheader("Upload New Document")
        uploaded_file = st.file_uploader(
            "Choose a PDF file",
            type=['pdf'],
            help="Upload legal documents for AI analysis"
        )
        
        if uploaded_file is not None:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"Selected: {uploaded_file.name}")
            with col2:
                if st.button("Upload", use_container_width=True):
                    self.upload_document(uploaded_file)
        
        # Document list section
        st.subheader("Uploaded Documents")
        
        if not st.session_state.documents_uploaded:
            self.load_document_list()
        
        if st.session_state.documents_uploaded:
            for doc in st.session_state.documents_uploaded:
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.write(f"**{doc.get('filename', 'Unknown')}**")
                
                with col2:
                    st.write(f"Chunks: {doc.get('chunk_count', 0)}")
                
                with col3:
                    if st.button("Delete", key=f"delete_{doc.get('document_id')}"):
                        self.delete_document(
                            doc.get('document_id'), 
                            doc.get('filename', 'Unknown')
                        )
        else:
            st.info("No documents uploaded yet. Upload a PDF to get started.")
    
    def render_analytics_dashboard(self):
        """Render analytics dashboard"""
        st.header("Analytics Dashboard")
        
        # System metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Total Messages</div>
            </div>
            """.format(len(st.session_state.messages)), unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value">{}</div>
                <div class="metric-label">Documents Uploaded</div>
            </div>
            """.format(len(st.session_state.documents_uploaded)), unsafe_allow_html=True)
        
        with col3:
            api_status_text = "Online" if st.session_state.api_status == "online" else "Offline"
            st.markdown("""
            <div class="metric-card">
                <div class="metric-value status-{}">{}</div>
                <div class="metric-label">API Status</div>
            </div>
            """.format(st.session_state.api_status, api_status_text), unsafe_allow_html=True)
        
        # Recent activity
        st.subheader("Recent Activity")
        recent_messages = st.session_state.messages[-5:] if st.session_state.messages else []
        
        if recent_messages:
            for msg in reversed(recent_messages):
                timestamp = datetime.fromisoformat(msg['timestamp']).strftime("%Y-%m-%d %H:%M")
                role = "User" if msg['role'] == 'user' else "Assistant"
                content_preview = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                
                st.markdown(f"""
                <div class="info-card">
                    <strong>{timestamp} - {role}:</strong><br>
                    {content_preview}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No recent activity to display.")
    
    def render_advanced_audit_logs(self):
        """Render advanced audit logs viewer with filters and export"""
        current_user = self.auth_manager.get_current_user()
        if not current_user or current_user['role'] != 'admin':
            st.error("Access denied. Admin privileges required.")
            return
        
        st.header("Advanced Audit Logs")
        
        # Log access to audit logs
        self.db_manager.log_audit_event(
            user_id=current_user['id'],
            username=current_user['username'],
            action_type="AUDIT_LOG_ACCESS",
            resource="audit_logs",
            status="success",
            details="Admin accessed audit log viewer",
            ip_address=self._get_client_ip(),
            session_id=self.session_id,
            severity_level="INFO"
        )
        
        # Initialize filter state
        if 'audit_filters' not in st.session_state:
            st.session_state.audit_filters = {
                'action_type': '',
                'username': '',
                'status': '',
                'severity_level': '',
                'date_from': '',
                'date_to': '',
                'page': 1
            }
        
        # Filters Section
        with st.expander("Filter Options", expanded=True):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                action_types = ['', 'LOGIN', 'CHAT', 'DOC_UPLOAD', 'DOC_DELETE', 'PASSWORD', 'USER_CREATE', 'AUDIT']
                st.session_state.audit_filters['action_type'] = st.selectbox(
                    "Action Type",
                    action_types,
                    index=action_types.index(st.session_state.audit_filters['action_type']) if st.session_state.audit_filters['action_type'] in action_types else 0
                )
                
                st.session_state.audit_filters['username'] = st.text_input(
                    "Username",
                    value=st.session_state.audit_filters['username'],
                    placeholder="Search by username..."
                )
            
            with col2:
                statuses = ['', 'success', 'failure', 'error', 'initiated']
                st.session_state.audit_filters['status'] = st.selectbox(
                    "Status",
                    statuses,
                    index=statuses.index(st.session_state.audit_filters['status']) if st.session_state.audit_filters['status'] in statuses else 0
                )
                
                severity_levels = ['', 'INFO', 'WARNING', 'ERROR']
                st.session_state.audit_filters['severity_level'] = st.selectbox(
                    "Severity Level",
                    severity_levels,
                    index=severity_levels.index(st.session_state.audit_filters['severity_level']) if st.session_state.audit_filters['severity_level'] in severity_levels else 0
                )
            
            with col3:
                st.session_state.audit_filters['date_from'] = st.date_input(
                    "Date From",
                    value=date.fromisoformat(st.session_state.audit_filters['date_from']) if st.session_state.audit_filters['date_from'] else None
                )
                if st.session_state.audit_filters['date_from']:
                    st.session_state.audit_filters['date_from'] = str(st.session_state.audit_filters['date_from'])
                else:
                    st.session_state.audit_filters['date_from'] = ''
                
                st.session_state.audit_filters['date_to'] = st.date_input(
                    "Date To",
                    value=date.fromisoformat(st.session_state.audit_filters['date_to']) if st.session_state.audit_filters['date_to'] else None
                )
                if st.session_state.audit_filters['date_to']:
                    st.session_state.audit_filters['date_to'] = str(st.session_state.audit_filters['date_to'])
                else:
                    st.session_state.audit_filters['date_to'] = ''
            
            # Action buttons
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("Apply Filters", use_container_width=True):
                    st.session_state.audit_filters['page'] = 1
                    st.rerun()
            
            with col2:
                if st.button("Clear Filters", use_container_width=True):
                    st.session_state.audit_filters = {
                        'action_type': '',
                        'username': '',
                        'status': '',
                        'severity_level': '',
                        'date_from': '',
                        'date_to': '',
                        'page': 1
                    }
                    st.rerun()
            
            with col3:
                if st.button("Export CSV", use_container_width=True):
                    csv_data = self.db_manager.export_audit_logs_csv(st.session_state.audit_filters)
                    if csv_data:
                        st.download_button(
                            label="Download CSV",
                            data=csv_data,
                            file_name=f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        # Log export action
                        self.db_manager.log_audit_event(
                            user_id=current_user['id'],
                            username=current_user['username'],
                            action_type="AUDIT_LOG_EXPORT",
                            resource="audit_logs",
                            status="success",
                            details=f"Exported audit logs with filters: {json.dumps(st.session_state.audit_filters)}",
                            ip_address=self._get_client_ip(),
                            session_id=self.session_id,
                            severity_level="INFO"
                        )
        
        # Get filtered logs
        page_size = 25
        logs, total_count = self.db_manager.get_audit_logs_filtered(
            page=st.session_state.audit_filters['page'],
            page_size=page_size,
            **{k: v for k, v in st.session_state.audit_filters.items() if k != 'page'}
        )
        
        # Display pagination info
        total_pages = (total_count + page_size - 1) // page_size
        st.markdown(f"**Showing page {st.session_state.audit_filters['page']} of {total_pages} ({total_count} total records)**")
        
        # Pagination controls
        if total_pages > 1:
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                if st.button("First", disabled=st.session_state.audit_filters['page'] == 1):
                    st.session_state.audit_filters['page'] = 1
                    st.rerun()
            
            with col2:
                if st.button("Previous", disabled=st.session_state.audit_filters['page'] == 1):
                    st.session_state.audit_filters['page'] -= 1
                    st.rerun()
            
            with col3:
                new_page = st.number_input(
                    "Page",
                    min_value=1,
                    max_value=total_pages,
                    value=st.session_state.audit_filters['page'],
                    step=1
                )
                if new_page != st.session_state.audit_filters['page']:
                    st.session_state.audit_filters['page'] = new_page
                    st.rerun()
            
            with col4:
                if st.button("Next", disabled=st.session_state.audit_filters['page'] == total_pages):
                    st.session_state.audit_filters['page'] += 1
                    st.rerun()
            
            with col5:
                if st.button("Last", disabled=st.session_state.audit_filters['page'] == total_pages):
                    st.session_state.audit_filters['page'] = total_pages
                    st.rerun()
        
        # Display logs
        if logs:
            for log in logs:
                # Status indicators (text-based, no emojis)
                status_indicators = {
                    'success': '[SUCCESS]',
                    'failure': '[FAILED]',
                    'error': '[ERROR]',
                    'initiated': '[INITIATED]'
                }
                status_indicator = status_indicators.get(log['status'], '[INFO]')
                
                timestamp = datetime.fromisoformat(log['timestamp']).strftime('%Y-%m-%d %H:%M:%S') if log['timestamp'] else 'Unknown'
                
                # Create a clean text-based display
                log_text = f"**{status_indicator} {log['action_type']}** - {timestamp}\n"
                log_text += f"User: {log['username']} | Status: {log['status']} | Severity: {log['severity_level']}\n"
                
                if log['resource']:
                    log_text += f"Resource: {log['resource']}\n"
                if log['ip_address']:
                    log_text += f"IP: {log['ip_address']}\n"
                if log['content_hash']:
                    log_text += f"Content Hash: {log['content_hash']}\n"
                if log['session_id']:
                    log_text += f"Session: {log['session_id'][:8]}...\n"
                if log['details']:
                    log_text += f"Details: {log['details']}\n"
                
                # Use colored containers based on severity
                if log['severity_level'] == 'ERROR':
                    st.error(log_text)
                elif log['severity_level'] == 'WARNING':
                    st.warning(log_text)
                else:
                    st.info(log_text)
                
                st.markdown("---")
        else:
            st.info("No audit logs found matching the current filters.")
        
        # Real-time refresh option
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Refresh Logs", use_container_width=True):
                st.rerun()
        
        with col2:
            auto_refresh = st.checkbox("Auto-refresh (30s)", value=False)
            if auto_refresh:
                import time
                time.sleep(30)
                st.rerun()

    def render_audit_logs(self):
        """Legacy audit logs method - redirect to advanced viewer"""
        self.render_advanced_audit_logs()
    
    def render_user_management(self):
        """Render comprehensive user management interface (Admin Only)"""
        if not self.auth_manager.check_admin_access("manage users"):
            return
        
        current_user = self.auth_manager.get_current_user()
        st.header("User Management")
        st.markdown("Manage user accounts, roles, and permissions")
        
        # Log access to user management
        self.db_manager.log_audit_event(
            user_id=current_user['id'],
            username=current_user['username'],
            action_type="USER_MANAGEMENT_ACCESS",
            resource="user_management",
            status="success",
            details="Admin accessed user management interface",
            ip_address=self._get_client_ip(),
            session_id=self.session_id,
            severity_level="INFO"
        )
        
        # User management tabs
        tab1, tab2, tab3 = st.tabs(["Manage Users", "Add User", "User Statistics"])
        
        with tab1:
            self._render_users_list()
        
        with tab2:
            self._render_add_user_form()
        
        with tab3:
            self._render_user_statistics()
    
    def _render_users_list(self):
        """Render the users list with management actions"""
        st.subheader("Current Users")
        
        users = self.db_manager.get_users()
        
        if not users:
            st.info("No users found.")
            return
        
        # Users table
        for user in users:
            with st.container():
                col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 2])
                
                with col1:
                    st.markdown(f"**{user['username']}**")
                    created_date = user['created_at'][:10] if user['created_at'] else 'Unknown'
                    st.caption(f"Created: {created_date}")
                
                with col2:
                    role_badge = "[Admin]" if user['role'] == 'admin' else "[User]"
                    st.markdown(f"{role_badge} {user['role'].title()}")
                
                with col3:
                    # Account status
                    if user.get('failed_login_attempts', 0) >= 5:
                        st.error("Locked")
                    else:
                        st.success("Active")
                
                with col4:
                    # Last login
                    if user.get('last_login'):
                        last_login = user['last_login'][:10]
                        st.text(f"Last: {last_login}")
                    else:
                        st.text("Never")
                
                with col5:
                    # Action buttons
                    action_col1, action_col2, action_col3 = st.columns(3)
                    
                    with action_col1:
                        # Change role button
                        if st.button("Change Role", key=f"role_{user['id']}", help="Change Role"):
                            st.session_state[f'change_role_{user["id"]}'] = True
                            st.rerun()
                    
                    with action_col2:
                        # Unlock account button
                        if user.get('failed_login_attempts', 0) >= 5:
                            if st.button("🔓", key=f"unlock_{user['id']}", help="Unlock Account"):
                                success = self.db_manager.reset_failed_login_attempts(
                                    user['id'], 
                                    self.auth_manager.get_current_user()['username'],
                                    self._get_client_ip()
                                )
                                if success:
                                    st.success(f"Account unlocked for {user['username']}")
                                    st.rerun()
                                else:
                                    st.error("Failed to unlock account")
                    
                    with action_col3:
                        # Delete user button (with protection)
                        current_admin = self.auth_manager.get_current_user()
                        can_delete = user['username'] != current_admin['username']  # Can't delete self
                        
                        if st.button("Delete", key=f"delete_{user['id']}", 
                                   help="Delete User" if can_delete else "Cannot delete yourself",
                                   disabled=not can_delete):
                            st.session_state[f'confirm_delete_{user["id"]}'] = True
                            st.rerun()
                
                # Role change dialog
                if st.session_state.get(f'change_role_{user["id"]}', False):
                    with st.form(f"change_role_form_{user['id']}"):
                        st.write(f"Change role for **{user['username']}**")
                        current_role = user['role']
                        new_role = st.selectbox(
                            "New Role",
                            options=['user', 'admin'],
                            index=0 if current_role == 'admin' else 1,
                            key=f"new_role_{user['id']}"
                        )
                        
                        col_submit, col_cancel = st.columns(2)
                        with col_submit:
                            if st.form_submit_button("Confirm"):
                                success = self.db_manager.change_user_role(
                                    user['id'], new_role,
                                    self.auth_manager.get_current_user()['username'],
                                    self._get_client_ip()
                                )
                                if success:
                                    st.success(f"Role changed to {new_role} for {user['username']}")
                                else:
                                    st.error("Failed to change role")
                                st.session_state[f'change_role_{user["id"]}'] = False
                                st.rerun()
                        
                        with col_cancel:
                            if st.form_submit_button("Cancel"):
                                st.session_state[f'change_role_{user["id"]}'] = False
                                st.rerun()
                
                # Delete confirmation dialog
                if st.session_state.get(f'confirm_delete_{user["id"]}', False):
                    st.error(f"**Delete user '{user['username']}'?**")
                    st.write("This action cannot be undone.")
                    
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("Delete", key=f"confirm_delete_{user['id']}"):
                            success = self.db_manager.delete_user(
                                user['id'],
                                self.auth_manager.get_current_user()['username'],
                                self._get_client_ip()
                            )
                            if success:
                                st.success(f"User {user['username']} deleted successfully")
                            else:
                                st.error("Failed to delete user")
                            st.session_state[f'confirm_delete_{user["id"]}'] = False
                            st.rerun()
                    
                    with col_cancel:
                        if st.button("Cancel", key=f"cancel_delete_{user['id']}"):
                            st.session_state[f'confirm_delete_{user["id"]}'] = False
                            st.rerun()
                
                st.markdown("---")
    
    def _render_add_user_form(self):
        """Render the add user form"""
        st.subheader("Add New User")
        
        with st.form("add_user_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                new_username = st.text_input(
                    "Username",
                    help="Choose a unique username (3-50 characters)",
                    placeholder="Enter username"
                )
            
            with col2:
                new_role = st.selectbox(
                    "Role",
                    options=['user', 'admin'],
                    help="Select user role"
                )
            
            new_password = st.text_input(
                "Password",
                type="password",
                help="Secure password (minimum 8 characters)",
                placeholder="Enter secure password"
            )
            
            confirm_password = st.text_input(
                "Confirm Password",
                type="password",
                help="Re-enter password to confirm",
                placeholder="Confirm password"
            )
            
            submit_button = st.form_submit_button("Create User", use_container_width=True)
            
            if submit_button:
                # Validation
                if not new_username or not new_password:
                    st.error("Username and password are required")
                elif len(new_username) < 3:
                    st.error("Username must be at least 3 characters long")
                elif len(new_password) < 8:
                    st.error("Password must be at least 8 characters long")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                else:
                    # Create user
                    success = self.db_manager.create_user(
                        username=new_username,
                        password=new_password,
                        role=new_role,
                        creator_username=self.auth_manager.get_current_user()['username'],
                        ip_address=self._get_client_ip()
                    )
                    
                    if success:
                        st.success(f"User '{new_username}' created successfully with role '{new_role}'")
                        # Clear form by rerunning
                        st.rerun()
                    else:
                        st.error("Failed to create user. Username may already exist.")
        
        # Password guidelines
        with st.expander("Password Security Guidelines"):
            st.markdown("""
            **Strong Password Requirements:**
            - Minimum 8 characters length
            - Mix of uppercase and lowercase letters
            - Include numbers and special characters
            - Avoid common words or personal information
            - Unique to this system
            """)
    
    def _render_user_statistics(self):
        """Render user statistics and insights"""
        st.subheader("User Statistics")
        
        users = self.db_manager.get_users()
        
        if not users:
            st.info("No user data available.")
            return
        
        # Basic stats
        total_users = len(users)
        admin_users = sum(1 for user in users if user['role'] == 'admin')
        regular_users = total_users - admin_users
        locked_accounts = sum(1 for user in users if user.get('failed_login_attempts', 0) >= 5)
        
        # Display metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Users", total_users)
        
        with col2:
            st.metric("Admin Users", admin_users)
        
        with col3:
            st.metric("Regular Users", regular_users)
        
        with col4:
            st.metric("Locked Accounts", locked_accounts)
        
        # Recent activity
        st.markdown("### Recent User Activity")
        recent_logs, _ = self.db_manager.get_audit_logs_filtered(
            page=1, 
            page_size=10,
            action_type="LOGIN"
        )
        
        if recent_logs:
            for log in recent_logs[:5]:  # Show last 5 login events
                timestamp = log['timestamp'][:19] if log['timestamp'] else 'Unknown'
                status_text = "[Success]" if log['status'] == 'success' else "[Failed]"
                st.text(f"{status_text} {log['username']} - {timestamp}")
        else:
            st.info("No recent login activity.")
    
    def run(self):
        """Main application loop"""
        # Apply theme first
        self.theme_manager.apply_theme()
        
        # Check authentication
        if not self.auth_manager.is_authenticated():
            self.auth_manager.show_login_page()
            return
        
        # Main authenticated app
        self.render_header()
        
        # Check API health on startup
        if st.session_state.api_status == "unknown":
            self.check_api_health()
        
        # Sidebar content
        self.render_api_status()
        self.auth_manager.show_user_menu()
        self.render_navigation()
        self.render_settings_sidebar()
        
        # Main content area based on current view
        if st.session_state.current_view == 'chat':
            self.render_chat_interface()
        elif st.session_state.current_view == 'documents':
            self.render_document_management()
        elif st.session_state.current_view == 'analytics':
            self.render_analytics_dashboard()
        elif st.session_state.current_view == 'audit':
            self.render_audit_logs()
        elif st.session_state.current_view == 'users':
            self.render_user_management()
        
        # Handle chat input (only show in chat view)
        if st.session_state.current_view == 'chat':
            self.handle_chat_input()

def main():
    """Main function to run the app"""
    st.set_page_config(
        page_title="Legal AI Assistant",
        page_icon=":material/balance:",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    app = LawFirmAIApp()
    app.run()

if __name__ == "__main__":
    main() 