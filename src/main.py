"""
Allegro IO Code Assistant - Main Application
Streamlit-based interface for code analysis using LLMs.
"""

import streamlit as st
from pathlib import Path
import sys
import os
from datetime import datetime
from typing import Dict, Any
import logging

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Deve essere la prima chiamata Streamlit
st.set_page_config(
    page_title="Allegro IO - Code Assistant",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aggiungi la directory root al path per permettere gli import relativi
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from src.core.session import SessionManager
from src.core.llm import LLMManager
from src.core.files import FileManager
from src.ui.layout import render_app_layout, render_error_message, render_success_message, render_info_message
from src.utils.config import load_config

def setup_directory_structure():
    """
    Verifica e crea la struttura delle directory necessarie.
    """
    required_dirs = {
        'templates': ['code_review', 'architecture', 'security'],
        'src/core': [],
        'src/ui': [],
        'src/utils': [],
        'logs': []
    }
    
    base_path = Path(__file__).parent.parent
    
    try:
        for dir_name, subdirs in required_dirs.items():
            dir_path = base_path / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)
            
            for subdir in subdirs:
                subdir_path = dir_path / subdir
                subdir_path.mkdir(exist_ok=True)
                
        logger.info("Directory structure setup completed")
    except Exception as e:
        logger.error(f"Error setting up directory structure: {e}")
        raise

def validate_environment() -> bool:
    """
    Valida l'ambiente e le configurazioni necessarie.
    
    Returns:
        bool: True se la validazione ha successo
    """
    required_secrets = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    missing_secrets = [secret for secret in required_secrets if secret not in st.secrets]
    
    if missing_secrets:
        render_error_message(
            f"Configurazione incompleta. Mancano le seguenti API keys: {', '.join(missing_secrets)}\n"
            "Configura le API keys in .streamlit/secrets.toml"
        )
        return False
    
    required_packages = ['openai', 'anthropic', 'watchdog']
    try:
        for package in required_packages:
            __import__(package)
    except ImportError as e:
        render_error_message(f"Pacchetto mancante: {str(e)}")
        return False
    
    return True

@st.cache_resource
def initialize_clients() -> Dict[str, Any]:
    """
    Inizializza e cachea i client necessari per l'applicazione.
    
    Returns:
        Dict[str, Any]: Dictionary contenente i client inizializzati
    """
    try:
        return {
            'llm': LLMManager(),
            'session': SessionManager(),
            'file_manager': FileManager()
        }
    except Exception as e:
        logger.error(f"Error initializing clients: {e}")
        raise

def load_custom_css():
    """
    Carica gli stili CSS personalizzati per l'applicazione.
    """
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
            background-color: #f8f9fa;
            padding: 1rem;
        }
        
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }
        
        /* Chat UI */
        .stChatFloatingInputContainer {
            bottom: 0 !important;
            background: white !important;
            padding: 1rem !important;
            z-index: 999999 !important;
            width: 100% !important;
            border-top: 1px solid #eee;
        }
        
        .stChatMessage {
            background: #f8f9fa;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 0.5rem;
        }
        
        /* Code blocks */
        pre {
            background-color: #2d2d2d;
            border-radius: 0.5rem;
            padding: 1rem;
        }
        
        code {
            font-family: 'Fira Code', monospace;
        }
        
        /* Custom components */
        .file-tree {
            font-family: monospace;
            white-space: pre;
        }
        
        .status-indicator {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 5px;
        }
        
        .status-online {
            background-color: #28a745;
        }
        
        .status-error {
            background-color: #dc3545;
        }
        </style>
    """, unsafe_allow_html=True)

def initialize_session_state():
    """
    Inizializza o recupera lo stato della sessione.
    """
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.start_time = datetime.now().isoformat()
        st.session_state.error_log = []
        st.session_state.debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'

def main():
    """
    Funzione principale dell'applicazione.
    Gestisce l'inizializzazione e il flusso principale.
    """
    try:
        # Step 1: Setup iniziale
        setup_directory_structure()
        
        # Step 2: Validazione ambiente
        if not validate_environment():
            st.stop()
        
        # Step 3: Caricamento configurazione
        config = load_config()
        
        # Step 4: Inizializzazione stato
        initialize_session_state()
        
        # Step 5: Inizializzazione clients
        clients = initialize_clients()
        
        # Step 6: Caricamento CSS
        load_custom_css()
        
        # Step 7: Renderizza l'interfaccia
        render_app_layout(clients)
        
        # Step 8: Debug mode
        if st.session_state.debug_mode:
            with st.expander("Debug Information", expanded=False):
                st.json({
                    'session_state': {
                        k: str(v) for k, v in st.session_state.items()
                        if k not in ['client_config', 'secrets']
                    },
                    'start_time': st.session_state.start_time,
                    'error_log': st.session_state.error_log
                })
        
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
        render_error_message(
            "Si è verificato un errore nell'applicazione. "
            "Per favore, controlla i log per maggiori dettagli."
        )
        
        if st.session_state.debug_mode:
            st.exception(e)
        
        # Aggiungi l'errore al log
        st.session_state.error_log.append({
            'timestamp': datetime.now().isoformat(),
            'error': str(e),
            'type': type(e).__name__
        })

if __name__ == "__main__":
    main()