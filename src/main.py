"""
Allegro IO Code Assistant - Main Application
Streamlit-based interface for code analysis using LLMs.
"""

import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import sys
import os
from datetime import datetime

from utils.config import init_app_config

# Force cache clear on startup
st.cache_data.clear()
st.cache_resource.clear()

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
from src.ui.components import FileExplorer, ChatInterface, ModelSelector, load_custom_css


def perform_full_reset():
    """
    Esegue un reset completo dell'applicazione con feedback visivo.
    Pulisce tutte le cache, lo stato della sessione e reinizializza i manager.
    """
    try:
        # Clear all Streamlit caches
        st.cache_data.clear()
        st.cache_resource.clear()
        
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        # Reset all managers
        SessionManager.init_session()
        
        # Reset API statistics
        st.session_state.message_stats = []
        st.session_state.total_stats = {
            'input_tokens': 0,
            'output_tokens': 0,
            'total_tokens': 0,
            'total_cost': 0.0
        }
        
        # Reset file management
        st.session_state.uploaded_files = {}
        st.session_state.file_messages_sent = set()
        
        # Reset chat state
        st.session_state.chats = {
            'Chat principale': {
                'messages': [],
                'created_at': datetime.now().isoformat()
            }
        }
        st.session_state.current_chat = 'Chat principale'
        
        # Reset model selection
        st.session_state.current_model = 'o1-mini'
        
        # Reinitialize configuration
        init_app_config()
        
        # Add success flag to session state
        st.session_state.show_reset_success = True
        
        # Force Streamlit to rerun
        st.rerun()
        
    except Exception as e:
        st.error(f"⚠️ Errore durante il reset: {str(e)}")


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
    # Initial setup
    clients = init_clients()
    clients['session'].init_session()
    
    # CSS per layout e posizionamento
    st.markdown("""
        <style>
        /* Chat container margins */
        div[data-testid="stChatMessageContainer"] {
            margin-bottom: 100px;
        }
        
        /* Fixed footer container */
        .stChatFloatingInputContainer {
            bottom: 0 !important;
            background: white !important;
            padding: 0 !important;
            padding-top: 8px !important;
        }

        /* Quick prompts styling */
        .st-emotion-cache-desfit {
            margin-bottom: 8px !important;
        }
        
        .stButton button {
            min-height: 32px !important;
            line-height: 1.1 !important;
            margin: 0 !important;
            background: #f0f2f6 !important;
            color: #31333F !important;
            border-radius: 16px !important;
            border: none !important;
        }
        
        .stButton button:hover {
            background: #e0e2e6 !important;
            color: #131415 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header area
    header_container = st.container()
    with header_container:
        col1, col2 = st.columns([6,1])
        with col1:
            st.title("👲🏿 Allegro")
        with col2:
            if st.button("🔄 Reset"):
                perform_full_reset()
                
        # Show success message if flag is set
        if st.session_state.get('show_reset_success', False):
            st.success("✅ Reset completato con successo!")
            # Clear the flag after showing the message
            del st.session_state.show_reset_success
        
    # Sidebar
    with st.sidebar:
        st.markdown("### 🤖 Model Settings")
        ModelSelector().render()
        st.markdown("---")
        st.markdown("### 📁 File Manager")
        FileExplorer().render()
    
    # Main Chat Area
    chat_container = st.container()
    with chat_container:
        st.markdown("### 💬 Chat")
        chat_interface = ChatInterface()
        chat_interface.render()
    
    # Footer con quick prompts e input
    cols = st.columns(4)
    prompts = chat_interface.quick_prompts.get(st.session_state.current_model, 
                                             chat_interface.quick_prompts['default'])
    # Quick prompts all'interno del container di input
    for i, prompt in enumerate(prompts):
        if cols[i % 4].button(prompt, key=f"quick_prompt_{i}", 
                            use_container_width=True):
            chat_interface.process_user_message(prompt)
    
    # Chat input
    if prompt := st.chat_input("Tu chiedere, io rispondere"):
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