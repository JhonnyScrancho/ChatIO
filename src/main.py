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
from src.ui.layout import render_app_layout, render_error_message
from src.utils.config import load_config

def check_environment():
    """Verifica la presenza delle secrets necessarie."""
    required_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    missing_vars = [var for var in required_vars if var not in st.secrets]
    
    if missing_vars:
        render_error_message(f"Secrets mancanti: {', '.join(missing_vars)}")
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

@st.cache_resource
def init_clients():
    """Inizializza e cachea i clients API."""
    return {
        'llm': LLMManager(),
        'session': SessionManager(),
        'file_manager': FileManager()
    }

def load_custom_css():
    """Carica stili CSS personalizzati."""
    st.markdown("""
        <style>
        /* Layout generale */
        .main {
            padding: 0 !important;
        }
        
        .block-container {
            padding-top: 1rem !important;
            max-width: 100% !important;
        }
        
        /* Sidebar migliorata */
        [data-testid="stSidebar"] {
            background-color: var(--surface-container);
        }
        
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
            color: var(--text-color);
        }
        
        /* Chat UI */
        .stChatFloatingInputContainer {
            bottom: 0 !important;
            background: white !important;
            padding: 1rem !important;
            z-index: 999999 !important;
            width: 100% !important;
        }
        
        /* ... resto del CSS ... */
        </style>
    """, unsafe_allow_html=True)

def main():
    """Funzione principale dell'applicazione."""
    try:
        # Carica variabili d'ambiente
        load_dotenv()
        
        # Controlli iniziali
        check_environment()
        check_directories()
        
        # Carica configurazione
        load_config()
        
        # Inizializza clients
        clients = init_clients()
        
        # Inizializza sessione
        clients['session'].init_session()
        
        # Carica CSS personalizzato
        load_custom_css()
        
        # Renderizza layout dell'applicazione
        render_app_layout(clients)
        
    except Exception as e:
        render_error_message(f"Si è verificato un errore: {str(e)}")
        if os.getenv('DEBUG') == 'True':
            st.exception(e)

if __name__ == "__main__":
    main()