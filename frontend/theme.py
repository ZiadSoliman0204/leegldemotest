"""
Theme management for Law Firm AI Assistant
Dark theme with high contrast and accessibility
"""

import streamlit as st
from typing import Dict

class ThemeManager:
    """Manages application dark theme with proper contrast ratios"""
    
    def __init__(self):
        self.initialize_theme()
    
    def initialize_theme(self):
        """Initialize theme settings in session state"""
        # Always use dark mode - no light mode support
        st.session_state.theme_mode = 'dark'
        
        if 'theme_initialized' not in st.session_state:
            self.apply_theme()
            st.session_state.theme_initialized = True
    
    def get_theme_colors(self) -> Dict[str, str]:
        """Get dark theme color palette with proper contrast"""
        return {
            # Dark mode - high contrast and accessibility
            'primary': '#4A90E2',
            'secondary': '#F5A623',
            'background': '#0E1117',          # Streamlit's default dark background
            'surface': '#262730',             # Slightly lighter for cards/surfaces
            'surface_variant': '#1E1E1E',     # For input fields and variants
            'text_primary': '#FAFAFA',        # High contrast white
            'text_secondary': '#CCCCCC',      # Light gray for secondary text
            'text_muted': '#9CA3AF',          # Muted text
            'border': '#3F3F3F',              # Visible borders in dark mode
            'success': '#10B981',             # Green for success states
            'warning': '#F59E0B',             # Amber for warnings
            'error': '#EF4444',               # Red for errors
            'info': '#3B82F6',                # Blue for info
            'input_bg': '#1E1E1E',            # Dark input backgrounds
            'card_bg': '#1A1A1A'              # Card backgrounds
        }
    
    def get_css_styles(self) -> str:
        """Generate CSS styles with proper contrast for dark theme"""
        colors = self.get_theme_colors()
        
        return f"""
        <style>
        /* Global app styling with high contrast */
        .stApp {{
            background-color: {colors['background']} !important;
            color: {colors['text_primary']} !important;
        }}
        
        /* Sidebar styling */
        .css-1d391kg {{
            background-color: {colors['surface']} !important;
        }}
        
        .css-1lcbmhc {{
            background-color: {colors['surface']} !important;
        }}
        
        /* Main content area */
        .main .block-container {{
            background-color: {colors['background']} !important;
            color: {colors['text_primary']} !important;
        }}
        
        /* Header styling */
        .main-header {{
            background: linear-gradient(135deg, {colors['primary']}, {colors['secondary']});
            color: white !important;
            padding: 2rem;
            border-radius: 12px;
            margin-bottom: 2rem;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        }}
        
        .main-header h1 {{
            color: white !important;
            margin: 0;
            font-size: 2.5rem;
            font-weight: 700;
        }}
        
        .main-header p {{
            color: white !important;
            margin: 0.5rem 0 0 0;
            font-size: 1.1rem;
            opacity: 0.9;
        }}
        
        /* Chat message styling with proper contrast */
        .chat-message {{
            padding: 1.2rem;
            margin: 1rem 0;
            border-radius: 12px;
            border-left: 4px solid {colors['primary']};
            background-color: {colors['card_bg']} !important;
            color: {colors['text_primary']} !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }}
        
        .user-message {{
            background-color: {colors['surface_variant']} !important;
            color: {colors['text_primary']} !important;
            margin-left: 2rem;
            border-left-color: {colors['secondary']};
        }}
        
        .assistant-message {{
            background-color: {colors['surface']} !important;
            color: {colors['text_primary']} !important;
            margin-right: 2rem;
            border-left-color: {colors['primary']};
        }}
        
        .chat-message strong {{
            color: {colors['text_primary']} !important;
            font-weight: 600;
        }}
        
        /* Card styling */
        .info-card {{
            background-color: {colors['card_bg']} !important;
            border: 1px solid {colors['border']};
            border-radius: 8px;
            padding: 1.2rem;
            margin: 0.8rem 0;
            color: {colors['text_primary']} !important;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }}
        
        .metric-card {{
            background-color: {colors['card_bg']} !important;
            border: 1px solid {colors['border']};
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            margin: 0.5rem;
            color: {colors['text_primary']} !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
        }}
        
        .metric-value {{
            font-size: 2.5rem;
            font-weight: bold;
            color: {colors['primary']} !important;
            margin-bottom: 0.5rem;
        }}
        
        .metric-label {{
            color: {colors['text_secondary']} !important;
            font-size: 0.9rem;
            font-weight: 500;
        }}
        
        /* Status indicators with proper contrast */
        .status-online {{
            color: {colors['success']} !important;
            font-weight: 600;
        }}
        
        .status-offline {{
            color: {colors['error']} !important;
            font-weight: 600;
        }}
        
        /* Form elements with proper contrast */
        .stTextInput > div > div > input {{
            background-color: {colors['input_bg']} !important;
            color: {colors['text_primary']} !important;
            border: 2px solid {colors['border']} !important;
            border-radius: 6px;
        }}
        
        .stTextInput > div > div > input:focus {{
            border-color: {colors['primary']} !important;
            box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.3);
        }}
        
        .stTextArea > div > div > textarea {{
            background-color: {colors['input_bg']} !important;
            color: {colors['text_primary']} !important;
            border: 2px solid {colors['border']} !important;
            border-radius: 6px;
        }}
        
        .stSelectbox > div > div > select {{
            background-color: {colors['input_bg']} !important;
            color: {colors['text_primary']} !important;
            border: 2px solid {colors['border']} !important;
        }}
        
        /* Button styling with proper contrast */
        .stButton > button {{
            background-color: {colors['primary']} !important;
            color: white !important;
            border: none !important;
            border-radius: 8px;
            padding: 0.6rem 1.2rem;
            font-weight: 600;
            transition: all 0.3s ease;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
        }}
        
        .stButton > button:hover {{
            background-color: {colors['secondary']} !important;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
        }}
        
        /* Sidebar text styling - ensure high contrast */
        .css-1d391kg .stMarkdown {{
            color: {colors['text_primary']} !important;
        }}
        
        .css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3 {{
            color: {colors['text_primary']} !important;
        }}
        
        /* Checkbox and radio styling */
        .stCheckbox > label {{
            color: {colors['text_primary']} !important;
        }}
        
        .stRadio > label {{
            color: {colors['text_primary']} !important;
        }}
        
        /* Slider styling */
        .stSlider > div > div > div > div {{
            background-color: {colors['primary']} !important;
        }}
        
        /* Markdown text styling - force high contrast */
        .stMarkdown {{
            color: {colors['text_primary']} !important;
        }}
        
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, 
        .stMarkdown h4, .stMarkdown h5, .stMarkdown h6 {{
            color: {colors['text_primary']} !important;
        }}
        
        .stMarkdown p {{
            color: {colors['text_primary']} !important;
        }}
        
        .stMarkdown strong {{
            color: {colors['text_primary']} !important;
        }}
        
        .stMarkdown ul, .stMarkdown ol {{
            color: {colors['text_primary']} !important;
        }}
        
        .stMarkdown li {{
            color: {colors['text_primary']} !important;
        }}
        
        /* Alert styling */
        .stSuccess {{
            background-color: {colors['success']} !important;
            color: white !important;
            border-radius: 6px;
        }}
        
        .stError {{
            background-color: {colors['error']} !important;
            color: white !important;
            border-radius: 6px;
        }}
        
        .stWarning {{
            background-color: {colors['warning']} !important;
            color: {colors['background']} !important;
            border-radius: 6px;
        }}
        
        .stInfo {{
            background-color: {colors['info']} !important;
            color: white !important;
            border-radius: 6px;
        }}
        
        /* File uploader styling */
        .stFileUploader {{
            background-color: {colors['surface']} !important;
            border: 2px dashed {colors['border']};
            border-radius: 8px;
            padding: 1rem;
        }}
        
        .stFileUploader label {{
            color: {colors['text_primary']} !important;
        }}
        
        /* Expander styling */
        .streamlit-expanderHeader {{
            background-color: {colors['surface']} !important;
            color: {colors['text_primary']} !important;
        }}
        
        .streamlit-expanderContent {{
            background-color: {colors['background']} !important;
            color: {colors['text_primary']} !important;
        }}
        
        /* Document item styling */
        .document-item {{
            background-color: {colors['card_bg']} !important;
            border: 1px solid {colors['border']};
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
            color: {colors['text_primary']} !important;
        }}
        
        .document-name {{
            font-weight: 600;
            color: {colors['text_primary']} !important;
        }}
        
        .document-info {{
            color: {colors['text_secondary']} !important;
            font-size: 0.9rem;
        }}
        
        /* Audit log styling */
        .audit-entry {{
            background-color: {colors['card_bg']} !important;
            border-left: 4px solid {colors['primary']};
            padding: 1rem;
            margin: 0.5rem 0;
            border-radius: 0 8px 8px 0;
            color: {colors['text_primary']} !important;
        }}
        
        .audit-timestamp {{
            color: {colors['text_muted']} !important;
            font-size: 0.85rem;
        }}
        
        .audit-action {{
            font-weight: 600;
            color: {colors['primary']} !important;
        }}
        
        /* Spinner styling */
        .stSpinner > div {{
            border-top-color: {colors['primary']} !important;
        }}
        
        /* Chat input styling */
        .stChatInput > div > div > input {{
            background-color: {colors['input_bg']} !important;
            color: {colors['text_primary']} !important;
            border: 2px solid {colors['border']} !important;
        }}
        
        /* Force text color in all containers */
        div[data-testid="stSidebar"] {{
            background-color: {colors['surface']} !important;
        }}
        
        div[data-testid="stSidebar"] * {{
            color: {colors['text_primary']} !important;
        }}
        
        /* Ensure proper contrast for metrics */
        .status-online {{
            color: {colors['success']} !important;
        }}
        
        .status-offline {{
            color: {colors['error']} !important;
        }}
        
        /* Fix any remaining white-on-white issues */
        div[data-testid="stSidebar"] .stMarkdown p,
        div[data-testid="stSidebar"] .stMarkdown h1,
        div[data-testid="stSidebar"] .stMarkdown h2,
        div[data-testid="stSidebar"] .stMarkdown h3,
        div[data-testid="stSidebar"] .stMarkdown h4,
        div[data-testid="stSidebar"] .stMarkdown h5,
        div[data-testid="stSidebar"] .stMarkdown h6 {{
            color: {colors['text_primary']} !important;
        }}
        
        /* Force high contrast for all text elements */
        * {{
            color: {colors['text_primary']} !important;
        }}
        
        /* Override for specific colored elements that should remain colored */
        .status-online,
        .status-offline,
        .audit-action,
        .metric-value,
        .main-header h1,
        .main-header p {{
            /* These will keep their specific colors defined above */
        }}
        
        /* Mobile responsiveness */
        @media (max-width: 768px) {{
            .main-header {{
                padding: 1rem;
                font-size: 1.2rem;
            }}
            
            .chat-message {{
                margin: 0.5rem 0.2rem;
                padding: 1rem;
            }}
            
            .user-message {{
                margin-left: 0.5rem;
            }}
            
            .assistant-message {{
                margin-right: 0.5rem;
            }}
        }}
        </style>
        """
    
    def apply_theme(self):
        """Apply dark theme to the application"""
        css_styles = self.get_css_styles()
        st.markdown(css_styles, unsafe_allow_html=True)
    
    def get_status_color(self, status: str) -> str:
        """Get color for status indicators"""
        colors = self.get_theme_colors()
        
        status_map = {
            'online': colors['success'],
            'offline': colors['error'],
            'unknown': colors['warning'],
            'warning': colors['warning'],
            'info': colors['info'],
            'primary': colors['primary'],
            'secondary': colors['secondary']
        }
        
        return status_map.get(status.lower(), colors['text_primary'])
    
    def render_status_indicator(self, status: str, text: str):
        """Render a status indicator with appropriate color"""
        color = self.get_status_color(status)
        if status == "unknown":
            icon = "⏳"
        elif status == "online":
            icon = "●"
        else:
            icon = "●"
        st.markdown(f'<span style="color: {color}; font-weight: 600;">{icon} {text}</span>', 
                   unsafe_allow_html=True) 