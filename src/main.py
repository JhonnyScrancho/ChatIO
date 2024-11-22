"""
Allegro IO Code Assistant - Main Application
Streamlit-based interface for code analysis using LLMs.
"""

import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import os
import sys

# Aggiungi la directory root al path per permettere gli import relativi
root_path = Path(__file__).parent.parent
sys.path.append(str(root_path))

from src.core.session import SessionManager
from src.core.llm import LLMManager
from src.core.files import FileManager
from src.ui.layout import render_main_layout
from src.utils.config import load_config

# Carica variabili d'ambiente
load_dotenv()

# Verifica configurazione base
def check_environment():
    """Verifica la presenza delle secrets necessari."""
    required_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    missing_vars = [var for var in required_vars if var not in st.secrets]
    
    if missing_vars:
        st.error(f"⚠️ Secrets mancanti: {', '.join(missing_vars)}")
        st.info("ℹ️ Configura le API keys in .streamlit/secrets.toml")
        st.stop()

# Verifica esistenza cartelle necessarie
def check_directories():
    """Verifica e crea le cartelle necessarie se non esistono."""
    required_dirs = ['templates']
    base_path = Path(__file__).parent.parent
    
    for dir_name in required_dirs:
        dir_path = base_path / dir_name
        if not dir_path.exists():
            st.warning(f"⚠️ Cartella {dir_name} mancante. Creazione in corso...")
            dir_path.mkdir(parents=True)

# Configurazione CSS personalizzato
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
        </style>
    """, unsafe_allow_html=True)

def main():
    """Funzione principale dell'applicazione."""
    # Controlli iniziali
    check_environment()
    check_directories()
    load_custom_css()
    
    try:
        # Import dopo i controlli per evitare errori
        from ui import render_main_layout
        from core import SessionManager, LLMManager, FileManager
        
        # Renderizza il layout principale
        render_main_layout()
        
    except Exception as e:
        st.error(f"❌ Si è verificato un errore: {str(e)}")
        if os.getenv('DEBUG') == 'True':
            st.exception(e)

if __name__ == "__main__":
    main()