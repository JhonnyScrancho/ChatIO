"""
Allegro IO Code Assistant - Main Application
Streamlit-based interface for code analysis using LLMs.
"""

import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
import os
import sys
from datetime import datetime

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
            padding: 1rem;
        }
        
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
            color: var(--text-color);
        }
        
        /* Chat container con spazio per input fisso */
        .chat-container {
            height: calc(100vh - 200px);
            overflow-y: auto;
            margin-bottom: 80px;
        }
        
        /* Input chat fisso */
        .stChatInputContainer, .stStreamlitMessageInputContainer {
            position: fixed !important;
            bottom: 0 !important;
            left: 18rem !important;
            right: 0 !important;
            background: white !important;
            padding: 1rem !important;
            border-top: 1px solid #eee !important;
            z-index: 1000 !important;
        }
        
        /* Chat message container */
        [data-testid="stChatMessageContainer"] {
            padding-bottom: 100px !important;
        }
        
        .stChatMessage {
            max-width: none !important;
            width: 100% !important;
            margin: 0.5rem 0 !important;
        }
        
        /* Code viewer */
        .code-viewer {
            background: #ffffff;
            border-radius: 0.5rem;
            border: 1px solid #eee;
            padding: 1rem;
            height: calc(100vh - 130px);
            overflow-y: auto;
        }
        
        .source {
            font-family: 'Courier New', Courier, monospace;
            font-size: 14px;
            line-height: 1.4;
            background-color: #272822;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }
        
        /* File explorer minimalista */
        .file-tree button {
            background: none !important;
            border: none !important;
            padding: 0.2rem 0.5rem !important;
            text-align: left !important;
            font-size: 0.9rem !important;
            color: var(--text-color) !important;
            width: 100% !important;
            margin: 0 !important;
        }
        
        .file-tree button:hover {
            background-color: var(--surface-container-highest) !important;
        }
        
        /* Loader animation */
        .thinking-loader {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 0.5rem;
            margin: 1rem 0;
        }
        
        /* Scrollbars */
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
        
        /* Tooltips */
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
        
        /* Sidebar buttons and inputs */
        [data-testid="stSidebar"] button {
            background-color: var(--surface-container-highest) !important;
            color: var(--text-color) !important;
        }

        [data-testid="stSidebar"] input {
            background-color: var(--surface-container-highest) !important;
            color: var(--text-color) !important;
        }
        </style>
    """, unsafe_allow_html=True)

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

@st.cache_resource
def init_clients():
    """Inizializza e cachea i clients API."""
    return {
        'llm': LLMManager(),
        'session': SessionManager(),
        'file_manager': FileManager()
    }

def init_session_state():
    """Inizializza lo stato della sessione se non esiste."""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.files = {}
        st.session_state.chats = {
            'Chat principale': {
                'messages': [{
                    "role": "assistant",
                    "content": "Ciao! Carica dei file e fammi delle domande su di essi."
                }],
                'created_at': datetime.now().isoformat()
            }
        }
        st.session_state.current_chat = 'Chat principale'
        st.session_state.selected_file = None
        st.session_state.token_count = 0
        st.session_state.cost = 0.0
        st.session_state.current_model = 'o1-mini'
        st.session_state.debug_mode = False
        st.session_state.model_usage = {
            'o1-mini': 0,
            'o1-preview': 0,
            'claude-3-5-sonnet-20241022': 0
        }

def main():
    """Funzione principale dell'applicazione."""
    try:
        # Controlli iniziali
        check_environment()
        check_directories()
        load_custom_css()
        
        # Setup iniziale della sessione e clients
        init_session_state()
        clients = init_clients()
        
        # Title Area con Stats
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.title("🎯 Allegro IO")
        with col2:
            st.metric("Tokens Used", f"{st.session_state.token_count:,}")
        with col3:
            st.metric("Cost ($)", f"${st.session_state.cost:.3f}")
        
        # Sidebar con File Manager e Model Selector
        with st.sidebar:
            st.markdown("### 📁 File Manager")
            FileExplorer().render()
            st.markdown("---")
            st.markdown("### 🤖 Model Settings")
            ModelSelector().render()
            
            if st.checkbox("Debug Mode", value=st.session_state.debug_mode):
                st.session_state.debug_mode = True
                st.markdown("### 🔧 Debug Info")
                st.json({
                    "session_state": {k: str(v) for k, v in st.session_state.items()},
                    "current_model": st.session_state.current_model,
                    "files_loaded": len(st.session_state.files)
                })
        
        # Main Content Area con Chat e Code Viewer
        col1, col2 = st.columns([3, 2])
        
        with col1:
            st.markdown("### 💬 Chat")
            
            # Container per la chat con scrolling
            chat_container = st.container()
            with chat_container:
                st.markdown('<div class="chat-container">', unsafe_allow_html=True)
                ChatInterface().render()
                st.markdown('</div>', unsafe_allow_html=True)
            
            # Chat input fisso nel footer
            st.markdown('<div class="chat-input-container">', unsafe_allow_html=True)
            if prompt := st.chat_input("Chiedi qualcosa sul tuo codice...", key="chat_input"):
                current_chat = st.session_state.chats[st.session_state.current_chat]
                current_chat['messages'].append({"role": "user", "content": prompt})
                
                # Preparazione del contesto usando LLMManager
                context = clients['llm'].get_files_context(
                    st.session_state.files,
                    st.session_state.selected_file
                )
                
                with st.spinner("Elaborazione in corso..."):
                    try:
                        response = "".join(list(clients['llm'].process_request(
                            prompt=prompt,
                            context=context,
                            model=st.session_state.current_model
                        )))
                        
                        # Aggiorna le statistiche di utilizzo del modello
                        if st.session_state.current_model in st.session_state.model_usage:
                            st.session_state.model_usage[st.session_state.current_model] += 1
                        
                        current_chat['messages'].append({
                            "role": "assistant", 
                            "content": response
                        })
                    except Exception as e:
                        st.error(f"Errore: {str(e)}")
                        if st.session_state.current_model != 'claude-3-5-sonnet-20241022':
                            st.info("Tentativo con Claude come fallback...")
                            prev_model = st.session_state.current_model
                            st.session_state.current_model = 'claude-3-5-sonnet-20241022'
                            try:
                                response = "".join(list(clients['llm'].process_request(
                                    prompt=prompt,
                                    context=context,
                                    model='claude-3-5-sonnet-20241022'
                                )))
                                
                                # Aggiorna statistiche anche per il fallback
                                st.session_state.model_usage['claude-3-5-sonnet-20241022'] += 1
                                
                                current_chat['messages'].append({
                                    "role": "assistant", 
                                    "content": response
                                })
                                # Ripristina il modello precedente
                                st.session_state.current_model = prev_model
                            except Exception as e:
                                st.error(f"Errore anche con Claude: {str(e)}")
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown("### 📝 Code Viewer")
            CodeViewer().render()
            
            if st.session_state.files:
                st.markdown("### 📊 Statistics")
                StatsDisplay().render()
        
    except Exception as e:
        st.error(f"❌ Si è verificato un errore: {str(e)}")
        if st.session_state.get('debug_mode', False):
            st.exception(e)
            st.json({
                "error_type": type(e).__name__,
                "error_details": str(e),
                "session_state": {k: str(v) for k, v in st.session_state.items()}
            })

if __name__ == "__main__":
    main()