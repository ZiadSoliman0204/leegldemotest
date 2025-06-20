"""
Production-grade Streamlit Frontend for Law Firm AI Assistant
Features: Authentication, themes, document management, analytics
"""

import streamlit as st
import requests
import os
from datetime import datetime
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
        self._initialize_session_state()
    
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
            'show_change_password': False
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
        """Render navigation menu"""
        with st.sidebar:
            st.header("Navigation")
            
            views = {
                'chat': 'Chat Assistant',
                'documents': 'Document Management',
                'analytics': 'Analytics Dashboard',
                'audit': 'Audit Logs (Admin Only)'
            }
            
            current_user = self.auth_manager.get_current_user()
            
            for view_key, view_name in views.items():
                # Skip audit logs for non-admin users
                if view_key == 'audit' and (not current_user or current_user['role'] != 'admin'):
                    continue
                
                if st.button(view_name, use_container_width=True):
                    st.session_state.current_view = view_key
                    st.rerun()
    
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
    
    def send_chat_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Send a chat message to the API"""
        try:
            payload = self._build_chat_payload(message)
            response = self._make_api_request(payload)
            
            if response.status_code == 200:
                return response.json()
            else:
                st.error(f"API Error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as error:
            st.error(f"Connection error: {str(error)}")
            self.auth_manager.log_user_action("CHAT_ERROR", f"Connection error: {str(error)}")
            return None
        except Exception as error:
            st.error(f"Unexpected error: {str(error)}")
            self.auth_manager.log_user_action("CHAT_ERROR", f"Unexpected error: {str(error)}")
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
        """Add a message to the chat history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        
        if sources:
            message["sources"] = sources
        
        st.session_state.messages.append(message)
    
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
            if st.button("Clear Chat History"):
                st.session_state.messages = []
                self.auth_manager.log_user_action("CHAT_CLEARED", "User cleared chat history")
                st.rerun()
    
    def upload_document(self, uploaded_file):
        """Upload and process a document"""
        try:
            with st.spinner(f"Processing {uploaded_file.name}..."):
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}
                response = requests.post(
                    f"{API_BASE_URL}/api/v1/documents/upload", 
                    files=files,
                    timeout=UPLOAD_TIMEOUT
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"Document processed successfully! {result['pages_processed']} chunks created.")
                    
                    # Log document upload
                    self.auth_manager.log_user_action(
                        "DOCUMENT_UPLOADED", 
                        f"Uploaded document: {uploaded_file.name}"
                    )
                    
                    # Refresh document list
                    self.load_document_list()
                else:
                    st.error(f"Upload failed: {response.text}")
                    
        except requests.exceptions.RequestException as error:
            st.error(f"Connection error during upload: {str(error)}")
        except Exception as error:
            st.error(f"Upload error: {str(error)}")
    
    def delete_document(self, document_id: str, filename: str):
        """Delete a document from the system"""
        try:
            response = requests.delete(f"{API_BASE_URL}/api/v1/documents/{document_id}")
            if response.status_code == 200:
                st.success(f"Document '{filename}' deleted successfully!")
                
                # Log document deletion
                self.auth_manager.log_user_action(
                    "DOCUMENT_DELETED", 
                    f"Deleted document: {filename}"
                )
                
                self.load_document_list()
            else:
                st.error(f"Failed to delete document: {response.text}")
                
        except Exception as error:
            st.error(f"Error deleting document: {str(error)}")
    
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
    
    def render_audit_logs(self):
        """Render audit logs (admin only)"""
        current_user = self.auth_manager.get_current_user()
        if not current_user or current_user['role'] != 'admin':
            st.error("Access denied. Admin privileges required.")
            return
        
        st.header("Audit Logs")
        
        # Get audit logs from database
        logs = self.db_manager.get_audit_logs(50)
        
        if logs:
            for log in logs:
                timestamp = log['timestamp']
                action_color = self.theme_manager.get_status_color('primary')
                
                st.markdown(f"""
                <div class="audit-entry">
                    <div class="audit-action" style="color: {action_color};">{log['action']}</div>
                    <div><strong>User:</strong> {log['username']}</div>
                    <div><strong>Details:</strong> {log['details']}</div>
                    <div class="audit-timestamp">{timestamp}</div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No audit logs available.")
    
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
        
        # Handle chat input (only show in chat view)
        if st.session_state.current_view == 'chat':
            self.handle_chat_input()

def main():
    """Main function to run the app"""
    st.set_page_config(
        page_title="Legal AI Assistant",
        page_icon="⚖️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    app = LawFirmAIApp()
    app.run()

if __name__ == "__main__":
    main() 