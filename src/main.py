"""
Allegro IO Code Assistant - Main Application
Streamlit-based interface for code analysis using LLMs.
"""

import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

# Configurazione pagina - DEVE essere la prima chiamata Streamlit
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
    required_dirs = ['templates']
    base_path = Path(__file__).parent.parent
    
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        if not dir_path.exists():
            st.warning(f"⚠️ Cartella {dir_name} mancante. Creazione in corso...")
            dir_path.mkdir(parents=True)

def load_custom_css():
    """Carica stili CSS personalizzati."""
    st.markdown("""
        <style>
        .stApp {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .source {
            font-family: 'Courier New', Courier, monospace;
            font-size: 14px;
            line-height: 1.4;
        }
        
        .stChatMessage {
            background-color: #f0f2f6;
            border-radius: 10px;
            padding: 10px;
            margin: 5px 0;
        }
        
        .file-explorer {
            background-color: #ffffff;
            border-radius: 5px;
            padding: 10px;
            margin: 5px 0;
        }
        
        .stats-container {
            background-color: #f8f9fa;
            border-radius: 5px;
            padding: 10px;
            margin-top: 10px;
        }
        </style>
    """, unsafe_allow_html=True)

def render_main_layout():
    """Renderizza il layout principale dell'applicazione."""
    # Setup iniziale della sessione
    session = SessionManager()
    session.init_session()
    
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