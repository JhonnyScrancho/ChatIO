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
            background-color: var(--background-color);
            padding: 1rem;
        }
        
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }

        [data-testid="stMetricLabel"] {
                height:40px;
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
        
        /* Code viewer */
        .code-viewer {
            background: var(--background-color);
            border-radius: 0.5rem;
            border: 1px solid var(--secondary-background-color);
            padding: 1rem;
            height: calc(100vh - 130px);
            overflow-y: auto;
        }
        
        .source {
            font-family: 'Courier New', Courier, monospace;
            font-size: 14px;
            line-height: 1.4;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
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
        
        /* Stats display */
        .stats-container {
            display: flex;
            justify-content: flex-end;
            gap: 1rem;
            padding: 0.5rem;
            background: var(--secondary-background-color);
            border-radius: 0.5rem;
            margin-bottom: 1rem;
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

def render_main_layout():
    """Renderizza il layout principale dell'applicazione."""
    # CSS per gestire il layout di pagina e input bar fisso
    st.markdown("""
        <style>
            /* Layout generale */
            .main .block-container {
                max-width: 100% !important;
                padding-top: 1rem !important;
                padding-right: 1rem !important;
                padding-left: 1rem !important;
                padding-bottom: 80px !important;
            }
            
            /* Chat input fisso */
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

            /* Code Viewer styling */
            .codeviewer-container {
                border-left: 1px solid var(--secondary-background-color);
                height: calc(100vh - 80px);
                overflow-y: auto;
                padding-left: 1rem;
            }

            /* Artifact styling */
            .artifact-container {
                margin: 1rem 0;
                padding: 1rem;
                border-radius: 0.5rem;
                border: 1px solid var(--secondary-background-color);
                background-color: var(--background-color);
            }

            /* Chat container adjustments */
            .chat-container {
                height: calc(100vh - 150px);
                overflow-y: auto;
                padding-right: 1rem;
            }

            /* Ensure code blocks are properly formatted */
            pre code {
                white-space: pre !important;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Setup iniziale della sessione
    clients = init_clients()
    clients['session'].init_session()
    
    # Title Area
    col1, col2 = st.columns([6, 1])
    with col1:
        st.title("👲🏿 Allegro IO")
    with col2:
        if st.session_state.get('debug_mode', False):
            if st.button("📊", help="Show Stats"):
                st.session_state.show_stats = not st.session_state.get('show_stats', False)
    
    # Sidebar con File Manager e Model Selector
    with st.sidebar:
        st.markdown("### 🤖 Model Settings")
        ModelSelector().render()
        st.markdown("---")
        st.markdown("### 📁 File Manager")
        FileExplorer().render()
    
    # Container principale diviso in chat e codeviewer
    chat_container, viewer_container = st.columns([3, 2])
    
    # Chat Area
    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        st.markdown("### 💬 Chat")
        chat_interface = ChatInterface()
        chat_interface.render()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Code Viewer Area
    with viewer_container:
        st.markdown('<div class="codeviewer-container">', unsafe_allow_html=True)
        st.markdown("### 📝 Code Viewer")
        code_viewer = CodeViewer()
        code_viewer.render()
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Chat input fisso in fondo
    if prompt := st.chat_input("Chiedi qualcosa sul tuo codice..."):
        # Gestione preliminare del prompt
        if prompt.strip():
            # Aggiungi il messaggio alla chat
            clients['session'].add_message_to_current_chat({
                "role": "user",
                "content": prompt
            })
            
            # Processa il messaggio con gestione degli artifact
            chat_interface.handle_user_input(prompt)
            
            # Forza il refresh del CodeViewer se necessario
            if st.session_state.get('current_artifact'):
                code_viewer.render_artifact(st.session_state.current_artifact)

    # Gestione degli stati e aggiornamento UI
    if st.session_state.get('show_stats', False):
        with st.expander("📊 Statistics", expanded=True):
            StatsDisplay().render()

def main():
    """Funzione principale dell'applicazione."""
    load_dotenv()
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