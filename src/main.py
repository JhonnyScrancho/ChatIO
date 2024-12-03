"""
Allegro IO Code Assistant - Main Application
Streamlit-based interface for code analysis using LLMs.
"""

import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import sys
import os

# Must be the first Streamlit call
st.set_page_config(
    page_title="Allegro IO - Code Assistant",
    page_icon="🎯",
    layout="wide"
)

# Add root directory to path for relative imports
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from src.core.session import SessionManager
from src.core.llm import LLMManager
from src.core.files import FileManager
from src.ui.components import FileExplorer, ChatInterface, ModelSelector

def load_custom_css():
    """Load custom CSS styles."""
    st.markdown("""
        <style>
        /* General Layout */
        .main {
            padding: 0 !important;
        }
        
        .block-container {
            padding-top: 1rem !important;
            max-width: 100% !important;
        }
        
        /* Enhanced Sidebar */
        [data-testid="stSidebar"] {
            background-color: var(--background-color);
            padding: 1rem;
        }
        
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }
        
        /* Chat UI */
        .stChatFloatingInputContainer {
            bottom: 0 !important;
            padding: 1rem 2rem !important;
            background: var(--background-color) !important;
            border-top: 1px solid var(--secondary-background-color) !important;
        }
        
        .stChatMessage {
            max-width: none !important;
            width: 100% !important;
            margin: 0.5rem 0 !important;
        }
        
        /* File explorer */
        .stButton > button {
            width: 100%;
            text-align: left !important;
            padding: 2px 8px !important;
            background: none !important;
            border: none !important;
            font-weight: normal !important;
        }
        
        .stButton > button:hover {
            background-color: var(--primary-color-light) !important;
            color: var(--primary-color) !important;
        }
        
        .element-container:has(button[kind="secondary"]) {
            margin: 0 !important;
            padding: 0 !important;
        }
        
        /* Content container */
        .content-container {
            margin-left: 1rem;
            margin-right: 1rem;
            max-width: 1200px;
            margin: 0 auto;
        }
        
        /* Scrollbars */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--secondary-background-color);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: var(--primary-color);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: var(--primary-color-dark);
        }
                
        </style>
    """, unsafe_allow_html=True)

def check_environment():
    """Verify required secrets are present."""
    required_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    missing_vars = [var for var in required_vars if var not in st.secrets]
    
    if missing_vars:
        st.error(f"⚠️ Missing secrets: {', '.join(missing_vars)}")
        st.info("ℹ️ Configure API keys in .streamlit/secrets.toml")
        st.stop()

def check_directories():
    """Check and create necessary directories if they don't exist."""
    required_dirs = ['templates', 'src/core', 'src/ui', 'src/utils']
    base_path = Path(__file__).parent.parent
    
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        if not dir_path.exists():
            st.warning(f"⚠️ Missing directory {dir_name}. Creating...")
            dir_path.mkdir(parents=True, exist_ok=True)

@st.cache_resource
def init_clients():
    """Initialize and cache API clients."""
    return {
        'llm': LLMManager(),
        'session': SessionManager(),
        'file_manager': FileManager()
    }

def render_main_layout():
    """Render the main application layout."""
    # CSS for page layout and fixed input bar
    st.markdown("""
        <style>
            /* General Layout */
            .main .block-container {
                max-width: 100% !important;
                padding-top: 1rem !important;
                padding-right: 1rem !important;
                padding-left: 1rem !important;
                padding-bottom: 80px !important;
            }
            
            /* Fixed Chat Input */
            .stChatInputContainer {
                position: fixed !important;
                bottom: 0 !important;
                left: 0 !important;
                width: 100% !important;
                padding: 1rem 2rem !important;
                background-color: var(--background-color) !important;
                border-top: 1px solid var(--secondary-background-color) !important;
                z-index: 999 !important;
            }

            /* Usage stats */
            .usage-stats {
                font-size: 0.9rem;
                color: var(--text-color-secondary);
                text-align: right;
                padding-top: 0.5rem;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Initial session setup
    clients = init_clients()
    clients['session'].init_session()
    
    # Title Area with usage stats
    with st.container():
        col1, col2, col3 = st.columns([6, 2, 2])
        with col1:
            st.title("👲🏿 Allegro IO")
        
        # Get total usage
        total_tokens, total_cost = SessionManager.get_total_usage()
        
        # Show only if we have any usage
        if total_tokens > 0:
            with col2:
                st.markdown(f"<div class='usage-stats'>**Tokens:** {total_tokens:,}</div>", 
                          unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div class='usage-stats'>**Cost:** ${total_cost:.4f}</div>", 
                          unsafe_allow_html=True)
    
    # Sidebar with File Manager and Model Selector
    with st.sidebar:
        st.markdown("### 🤖 Model Settings")
        ModelSelector().render()
        st.markdown("---")
        st.markdown("### 📁 File Manager")
        FileExplorer().render()
    
    # Main Content Area with Chat in a centered container
    chat_container = st.container()
    with chat_container:
        st.markdown("### 💬 Chat")
        chat_interface = ChatInterface()
        chat_interface.render()
    
        # Add some spacing before the input to account for the fixed position
        st.markdown("<div style='height: 80px'></div>", unsafe_allow_html=True)
    
    # Fixed chat input at bottom
    if prompt := st.chat_input("Ask something about your code..."):
        clients['session'].add_message_to_current_chat({
            "role": "user",
            "content": prompt
        })
        chat_interface.process_user_message(prompt)

def main():
    """Main application function."""
    load_dotenv()
    try:
        # Initial checks
        check_environment()
        check_directories()
        load_custom_css()
        
        # Render main layout
        render_main_layout()
        
    except Exception as e:
        st.error(f"❌ An error occurred: {str(e)}")
        if os.getenv('DEBUG') == 'True':
            st.exception(e)

if __name__ == "__main__":
    main()