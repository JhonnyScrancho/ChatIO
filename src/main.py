"""
Allegro IO Code Assistant - Main Application
Streamlit-based interface for code analysis using LLMs.
"""

import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from anthropic import Anthropic
import pygments
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter
import zipfile
from io import BytesIO

# Deve essere la prima chiamata Streamlit
st.set_page_config(
    page_title="Allegro IO - Code Assistant",
    page_icon="🎯",
    layout="wide"
)

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

# Inizializzazione clients
@st.cache_resource
def init_clients():
    return {
        'openai': OpenAI(api_key=st.secrets["OPENAI_API_KEY"]),
        'anthropic': Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
    }

def check_environment():
    """Verifica la presenza delle secrets necessarie."""
    if 'OPENAI_API_KEY' not in st.secrets or 'ANTHROPIC_API_KEY' not in st.secrets:
        st.error("⚠️ API keys mancanti. Configura le API keys in .streamlit/secrets.toml")
        st.stop()

def initialize_session():
    """Inizializza lo stato della sessione."""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.chat_history = []
        st.session_state.current_model = 'o1-mini'
        st.session_state.files = {}
        st.session_state.current_file = None
        st.session_state.token_count = 0
        st.session_state.cost = 0.0
        st.session_state.clients = init_clients()

def process_file(uploaded_file):
    """Processa un singolo file."""
    if uploaded_file.size > MAX_FILE_SIZE:
        st.warning(f"File {uploaded_file.name} troppo grande. Massimo 5MB consentiti.")
        return None
    
    try:
        content = uploaded_file.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        # Determina il linguaggio
        try:
            lexer = get_lexer_for_filename(uploaded_file.name)
            language = lexer.name.lower()
        except:
            language = 'text'
            
        return {
            'content': content,
            'language': language,
            'size': len(content)
        }
    except Exception as e:
        st.warning(f"Errore nel processare {uploaded_file.name}: {str(e)}")
        return None

def process_zip(zip_file):
    """Processa un file ZIP."""
    processed_files = {}
    total_size = 0
    
    with zipfile.ZipFile(BytesIO(zip_file.read()), 'r') as zip_ref:
        for file_info in zip_ref.infolist():
            if file_info.file_size > MAX_FILE_SIZE:
                continue
                
            # Skip directories and hidden files
            if file_info.filename.endswith('/') or '/.' in file_info.filename:
                continue
                
            # Check extension
            ext = os.path.splitext(file_info.filename)[1].lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
                
            try:
                content = zip_ref.read(file_info.filename).decode('utf-8')
                try:
                    lexer = get_lexer_for_filename(file_info.filename)
                    language = lexer.name.lower()
                except:
                    language = 'text'
                    
                processed_files[file_info.filename] = {
                    'content': content,
                    'language': language,
                    'size': file_info.file_size
                }
                total_size += file_info.file_size
                
                if total_size > MAX_FILE_SIZE * 3:  # Limite totale ZIP
                    break
                    
            except Exception:
                continue
                
    return processed_files

def highlight_code(content: str, language: str) -> str:
    """Applica syntax highlighting al codice."""
    try:
        lexer = get_lexer_for_filename(f"file.{language}")
    except:
        lexer = TextLexer()
        
    formatter = HtmlFormatter(
        style='monokai',
        linenos=True,
        cssclass='source'
    )
    
    return pygments.highlight(content, lexer, formatter)

def render_sidebar():
    """Renderizza la sidebar."""
    with st.sidebar:
        st.markdown("### 📁 File Manager")
        uploaded_files = st.file_uploader(
            "Upload Files",
            accept_multiple_files=True,
            type=[ext[1:] for ext in ALLOWED_EXTENSIONS]
        )
        
        if uploaded_files:
            for file in uploaded_files:
                if file.name.endswith('.zip'):
                    files = process_zip(file)
                    st.session_state.files.update(files)
                else:
                    result = process_file(file)
                    if result:
                        st.session_state.files[file.name] = result
        
        st.markdown("### 🤖 Model")
        models = {
            'o1-mini': '🚀 O1 Mini (Fast)',
            'o1-preview': '🔍 O1 Preview (Advanced)',
            'claude-3-5-sonnet': '🎭 Claude 3.5 Sonnet (Detailed)'
        }
        selected_model = st.selectbox(
            "Select Model",
            list(models.keys()),
            format_func=lambda x: models[x],
            index=list(models.keys()).index(st.session_state.current_model)
        )
        if selected_model != st.session_state.current_model:
            st.session_state.current_model = selected_model
            st.experimental_rerun()

def process_llm_request(prompt: str, model: str):
    """Processa una richiesta al modello LLM."""
    try:
        if model.startswith('o1'):
            completion = st.session_state.clients['openai'].chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        else:  # Claude
            message = st.session_state.clients['anthropic'].messages.create(
                model="claude-3-5-sonnet",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            
            for chunk in message:
                if chunk.delta.text:
                    yield chunk.delta.text
                    
    except Exception as e:
        st.error(f"Errore durante la chiamata al modello: {str(e)}")
        yield "Mi dispiace, si è verificato un errore durante l'elaborazione della richiesta."

def render_main_content():
    """Renderizza il contenuto principale."""
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 💬 Chat Interface")
        
        # Chat history
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask about your code..."):
            with st.chat_message("user"):
                st.markdown(prompt)
            st.session_state.chat_history.append({
                "role": "user",
                "content": prompt
            })
            
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                for chunk in process_llm_request(prompt, st.session_state.current_model):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
                
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": full_response
                })
    
    with col2:
        st.markdown("### 📝 Code Viewer")
        if st.session_state.files:
            selected_file = st.selectbox(
                "Select file to view",
                options=list(st.session_state.files.keys())
            )
            if selected_file:
                file_data = st.session_state.files[selected_file]
                highlighted_code = highlight_code(
                    file_data['content'],
                    file_data['language']
                )
                st.markdown(f"**{selected_file}** ({file_data['language']})")
                st.markdown(highlighted_code, unsafe_allow_html=True)
                
                # CSS per syntax highlighting
                st.markdown("""
                    <style>
                        .source {
                            background-color: #272822;
                            padding: 10px;
                            border-radius: 5px;
                            overflow-x: auto;
                        }
                        .source .linenos {
                            color: #8f908a;
                            padding-right: 10px;
                        }
                        .source pre {
                            margin: 0;
                            color: #f8f8f2;
                        }
                    </style>
                """, unsafe_allow_html=True)

def main():
    """Funzione principale dell'applicazione."""
    try:
        check_environment()
        initialize_session()
        
        # Header
        st.title("🎯 Allegro IO - Code Assistant")
        
        # Layout principale
        render_sidebar()
        render_main_content()
        
    except Exception as e:
        st.error(f"❌ Si è verificato un errore: {str(e)}")
        if os.getenv('DEBUG') == 'True':
            st.exception(e)

if __name__ == "__main__":
    main()