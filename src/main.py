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
            background-color: #f8f9fa;
            padding: 1rem;
        }
        
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
            font-size: 0.9rem;
            margin-bottom: 0.5rem;
        }
        
        /* Chat UI */
        .stChatFloatingInputContainer {
            position: fixed !important;
            bottom: 0 !important;
            left: 18rem !important;
            right: 0 !important;
            padding: 1rem 2rem !important;
            background: white !important;
            border-top: 1px solid #eee !important;
            z-index: 1000 !important;
        }
        
        .stChatMessage {
            max-width: none !important;
            width: 100% !important;
            margin: 0.5rem 0 !important;
        }
        
        /* Spazio per l'input fisso */
        [data-testid="stChatMessageContainer"] {
            padding-bottom: 80px !important;
            position: fixed !important;
            bottom: 0 !important;
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
            color: #0e1117 !important;
            width: 100% !important;
            margin: 0 !important;
        }
        
        .file-tree button:hover {
            background-color: #eef2f5 !important;
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
        
        .loader-dots {
            display: inline-flex;
            gap: 0.3rem;
        }
        
        .loader-dots span {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background-color: #666;
            animation: loader 1.4s infinite;
        }
        
        .loader-dots span:nth-child(2) { animation-delay: 0.2s; }
        .loader-dots span:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes loader {
            0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
            40% { opacity: 1; transform: scale(1); }
        }
        
        /* Stats display */
        .stats-container {
            display: flex;
            justify-content: flex-end;
            gap: 1rem;
            padding: 0.5rem;
            background: #f8f9fa;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
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
        <style>
        /* Header e Titolo */
        .stApp > header {
            background-color: transparent;
        }
        
        .main-header {
            display: flex;
            align-items: center;
            padding: 1rem 0;
            margin-bottom: 2rem;
        }
        
        .main-header h1 {
            font-size: 2.5rem;
            line-height: 1.2;
            margin: 0;
            padding: 0;
        }
        
        /* Metriche nell'header */
        [data-testid="metric-container"] {
            background-color: #1E1E1E;
            padding: 10px 15px;
            border-radius: 8px;
            width: auto;
            border: 1px solid #333;
        }
        
        [data-testid="metric-container"] > div {
            width: auto;
        }
        
        [data-testid="metric-container"] label {
            color: #CCC;
            font-size: 0.875rem;
            display: block;
            margin-bottom: 4px;
        }
        
        [data-testid="metric-container"] div[data-testid="metric-value"] {
            color: white;
            font-size: 1.25rem;
            font-weight: 600;
        }
        
        /* Bottoni migliorati */
        .stButton > button {
            border-radius: 6px;
            padding: 0.5rem 1rem;
            font-weight: 500;
            transition: all 0.2s ease;
            border: 1px solid rgba(250, 250, 250, 0.2);
            background-color: #2E2E2E;
        }
        
        .stButton > button:hover {
            background-color: #404040;
            border-color: rgba(250, 250, 250, 0.3);
            transform: translateY(-1px);
        }
        
        /* Bottoni specifici */
        [data-testid="baseButton-secondary"] {
            background-color: transparent !important;
            border-color: #4CAF50 !important;
            color: #4CAF50 !important;
        }
        
        [data-testid="baseButton-secondary"]:hover {
            background-color: rgba(76, 175, 80, 0.1) !important;
        }
        
        /* Layout della chat */
        .main .block-container {
            padding-top: 0 !important;
            max-width: 100% !important;
        }
        
        /* Stili per il selettore della chat */
        .stSelectbox {
            min-width: 200px;
        }
        
        .stSelectbox > div > div {
            background-color: #2E2E2E;
            border: 1px solid rgba(250, 250, 250, 0.2);
            border-radius: 6px;
        }
        
        /* Fix line-height per titoli */
        h1, h2, h3 {
            line-height: 1.2 !important;
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
    # CSS per gestire correttamente il layout di pagina
    st.markdown("""
        <style>
            /* Layout principale */
            .main .block-container {
                max-width: 100% !important;
                padding-top: 1rem !important;
                padding-right: 1rem !important;
                padding-left: 1rem !important;
                padding-bottom: 80px !important;   /* Spazio per il footer */
            }

            /* Stile input chat */
            .stChatFloatingInputContainer {
                bottom: 0;
                background: white;
                padding: 1rem;
                z-index: 999999;
                width: 100%;
            }

            /* Header metrics */
            [data-testid="metric-container"] {
                background-color: #1E1E1E;
                padding: 10px 15px;
                border-radius: 8px;
                width: auto;
                border: 1px solid #333;
            }
            
            [data-testid="metric-container"] label {
                color: #CCC;
                font-size: 0.875rem;
                display: block;
                margin-bottom: 4px;
            }
            
            [data-testid="metric-container"] div[data-testid="metric-value"] {
                color: white;
                font-size: 1.25rem;
                font-weight: 600;
            }

            /* Title area */
            .main-header h1 {
                margin: 0;
                padding: 0;
                line-height: 1.2;
            }
        </style>
    """, unsafe_allow_html=True)
    
    # Setup iniziale della sessione
    clients = init_clients()
    clients['session'].init_session()
    
    # Header Area con Title e Metrics
    header_container = st.container()
    with header_container:
        cols = st.columns([4, 2, 2])
        with cols[0]:
            st.markdown('<div class="main-header"><h1>👲🏿 Allegro IO</h1></div>', unsafe_allow_html=True)
        with cols[1]:
            st.metric(label="Tokens Used", value=f"{st.session_state.get('token_count', 0):,}")
        with cols[2]:
            st.metric(label="Cost ($)", value=f"${st.session_state.get('cost', 0):.3f}")
    
    # Sidebar con File Manager e Model Selector
    with st.sidebar:
        st.markdown("### 📁 File Manager")
        FileExplorer().render()
        st.markdown("---")
        st.markdown("### 🤖 Model Settings")
        ModelSelector().render()
    
    # Main Content Area con Chat e Code Viewer
    col1, col2 = st.columns([3, 2])
    
    with col1:
        st.markdown("### 💬 Chat")
        ChatInterface().render()
    
    with col2:
        st.markdown("### 📝 Code Viewer")
        CodeViewer().render()
    
    # Chat input al fondo della pagina
    chat_input_container = st.empty()
    
    # Inserisci l'input nel container vuoto
    with chat_input_container:
        if prompt := st.chat_input("Chiedi qualcosa sul tuo codice...", key="chat_input"):
            current_chat = st.session_state.chats[st.session_state.current_chat]
            current_chat['messages'].append({"role": "user", "content": prompt})
            
            with st.spinner("Elaborazione in corso..."):
                response = clients['llm'].process_request(prompt)
                current_chat['messages'].append({
                    "role": "assistant", 
                    "content": "".join(response)
                })
            st.rerun()

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