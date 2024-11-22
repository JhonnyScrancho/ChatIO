"""
Allegro IO Code Assistant - Main Application
Streamlit-based interface for code analysis using LLMs.
"""

import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv

# Deve essere la prima chiamata Streamlit
st.set_page_config(
    page_title="Allegro IO - Code Assistant",
    page_icon="🎯",
    layout="wide"
)

# Carica variabili d'ambiente
load_dotenv()

# Controllo ambiente
def check_environment():
    if 'OPENAI_API_KEY' not in st.secrets or 'ANTHROPIC_API_KEY' not in st.secrets:
        st.error("⚠️ API keys mancanti. Configura le API keys in .streamlit/secrets.toml")
        st.stop()

def initialize_session():
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.chat_history = []
        st.session_state.current_model = 'o1-mini'
        st.session_state.files = {}
        st.session_state.current_file = None
        st.session_state.token_count = 0
        st.session_state.cost = 0.0

def render_sidebar():
    with st.sidebar:
        st.markdown("### 📁 File Manager")
        uploaded_files = st.file_uploader(
            "Upload Files",
            accept_multiple_files=True,
            type=['py', 'js', 'txt', 'json', 'md']
        )
        
        if uploaded_files:
            for file in uploaded_files:
                content = file.read().decode('utf-8')
                st.session_state.files[file.name] = content
        
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
        st.session_state.current_model = selected_model

def render_main_content():
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
                st.markdown(f"Using model: {st.session_state.current_model}")
                st.markdown("Sample response - API integration pending")
    
    with col2:
        st.markdown("### 📝 Code Viewer")
        if st.session_state.files:
            selected_file = st.selectbox(
                "Select file to view",
                options=list(st.session_state.files.keys())
            )
            if selected_file:
                st.code(st.session_state.files[selected_file], language='python')

def main():
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