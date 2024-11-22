"""
Allegro IO Code Assistant - Main Application
Streamlit-based interface for code analysis using LLMs.
"""

import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

# Deve essere la prima chiamata Streamlit
st.set_page_config(
    page_title="Allegro IO - Code Assistant",
    page_icon="🎯",
    layout="wide"
)

# Aggiungi la directory root al path per permettere gli import relativi
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from src.core.session import SessionManager
from src.core.llm import LLMManager
from src.core.files import FileManager
from src.ui.components import FileExplorer, ChatInterface, CodeViewer, ModelSelector, StatsDisplay

# Carica variabili d'ambiente
load_dotenv()

# Configurazioni globali
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_EXTENSIONS = {
    '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css',
    '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php',
    '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sh',
    '.sql', '.md', '.txt', '.json', '.yml', '.yaml'
}

def check_environment():
    """Verifica la presenza delle secrets necessari."""
    required_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    missing_vars = [var for var in required_vars if var not in st.secrets]
    
    if missing_vars:
        st.error(f"⚠️ Secrets mancanti: {', '.join(missing_vars)}")
        st.info("ℹ️ Configura le API keys in .streamlit/secrets.toml")
        st.stop()

def check_directories():
    """Verifica e crea le cartelle necessarie se non esistono."""
    required_dirs = ['templates', 'src/core', 'src/ui', 'src/utils']
    base_path = Path(__file__).parent.parent
    
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        if not dir_path.exists():
            st.warning(f"⚠️ Cartella {dir_name} mancante. Creazione in corso...")
            dir_path.mkdir(parents=True, exist_ok=True)

def load_custom_css():
    """Carica stili CSS personalizzati."""
    st.markdown("""
        <style>
        /* Stile generale */
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        /* Stile code viewer */
        .source {
            font-family: 'Courier New', Courier, monospace;
            font-size: 14px;
            line-height: 1.4;
            background-color: #272822;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
        
        .source .linenos {
            color: #8f908a;
            padding-right: 10px;
            user-select: none;
        }
        
        .source pre {
            margin: 0;
            color: #f8f8f2;
        }
        
        /* Stile chat messages */
        .stChatMessage {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 10px;
            margin: 5px 0;
        }
        
        /* Stile file explorer */
        .file-explorer {
            background-color: #ffffff;
            border-radius: 5px;
            padding: 10px;
            margin: 5px 0;
        }
        
        /* Stile stats */
        .stats-container {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 10px;
            margin-top: 10px;
        }
        
        /* Stile buttons e inputs */
        .stButton>button {
            border-radius: 5px;
            transition: all 0.2s ease;
        }
        
        .stButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Stile scrollbars */
        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        
        /* Stile tooltips */
        .tooltip {
            position: relative;
            display: inline-block;
        }
        
        .tooltip .tooltiptext {
            visibility: hidden;
            background-color: #555;
            color: #fff;
            text-align: center;
            padding: 5px;
            border-radius: 4px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            transform: translateX(-50%);
            opacity: 0;
            transition: opacity 0.3s;
        }
        
        .tooltip:hover .tooltiptext {
            visibility: visible;
            opacity: 1;
        }
        </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def init_clients():
    """Inizializza e cachea i clients API."""
    return {
        'llm': LLMManager(),
        'session': SessionManager(),
        'file_manager': FileManager()
    }

def render_main_layout():
    """Renderizza il layout principale dell'applicazione."""
    # Setup iniziale della sessione
    clients = init_clients()
    clients['session'].init_session()
    
    # Title Area
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🎯 Allegro IO - Code Assistant")
    with col2:
        StatsDisplay().render()
    
    # Main Layout con Sidebar
    with st.sidebar:
        st.markdown("### 📁 File Manager")
        FileExplorer().render()
        st.markdown("---")
        st.markdown("### 🤖 Model Settings")
        ModelSelector().render()
    
    # Main Content Area
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("### 💬 Chat Interface")
        ChatInterface().render()
    
    with col2:
        st.markdown("### 📝 Code Viewer")
        CodeViewer().render()

def main():
    """Funzione principale dell'applicazione."""
    try:
        # Controlli iniziali
        check_environment()
        check_directories()
        load_custom_css()
        
        # Renderizza il layout principale
        render_main_layout()
        
    except Exception as e:
        st.error(f"❌ Si è verificato un errore: {str(e)}")
        if os.getenv('DEBUG') == 'True':
            st.exception(e)

if __name__ == "__main__":
    main()