"""
Main layout management for Allegro IO Code Assistant.
"""

import streamlit as st
from src.ui.components import FileExplorer, ChatInterface, CodeViewer, ModelSelector

def render_error_message(error: str):
    """Renderizza un messaggio di errore."""
    st.error(f"❌ {error}")

def render_success_message(message: str):
    """Renderizza un messaggio di successo."""
    st.success(f"✅ {message}")

def render_info_message(message: str):
    """Renderizza un messaggio informativo."""
    st.info(f"ℹ️ {message}")

def handle_chat_input(clients: dict, prompt: str):
    """
    Gestisce l'elaborazione dell'input della chat.
    
    Args:
        clients: Dictionary contenente i client necessari
        prompt: Input dell'utente
    """
    current_chat = st.session_state.chats[st.session_state.current_chat]
    
    # Aggiungi il contesto dei file al prompt se ci sono file caricati
    context = ""
    if st.session_state.get('uploaded_files'):
        current_file = st.session_state.get('current_file')
        if current_file and current_file in st.session_state.uploaded_files:
            file_info = st.session_state.uploaded_files[current_file]
            context = f"\nFile corrente: {current_file}\n```{file_info['language']}\n{file_info['content']}\n```"
    
    # Processa la richiesta
    with st.spinner("Elaborazione in corso..."):
        response = "".join(list(clients['llm'].process_request(
            prompt=prompt,
            context=context
        )))
        
        # Aggiungi i messaggi alla chat
        current_chat['messages'].extend([
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": response}
        ])

def render_app_layout(clients: dict):
    """
    Renderizza il layout principale dell'applicazione.
    
    Args:
        clients: Dictionary contenente i client necessari (llm, session, file_manager)
    """
    # Title Area con Stats
    col1, col2, col3 = st.columns([4, 1, 1])
    with col1:
        st.title("👲🏿 Allegro IO")
    with col2:
        st.metric("Tokens Used", f"{st.session_state.get('token_count', 0):,}")
    with col3:
        st.metric("Cost ($)", f"${st.session_state.get('cost', 0):.3f}")
    
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
    
    # Chat input
    prompt = st.chat_input("Chiedi qualcosa sul tuo codice...", key="chat_input")
    if prompt:
        handle_chat_input(clients, prompt)
        st.rerun()

# Esporta le funzioni necessarie
__all__ = [
    'render_app_layout',
    'render_error_message',
    'render_success_message',
    'render_info_message'
]