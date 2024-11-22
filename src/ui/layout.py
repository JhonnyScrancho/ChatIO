"""
Main layout management for Allegro IO Code Assistant.
"""

import streamlit as st
from src.ui.components import FileExplorer, ChatInterface, CodeViewer, ModelSelector, StatsDisplay
from src.core.session import SessionManager

# Configurazione della pagina - DEVE essere la prima chiamata Streamlit
st.set_page_config(
    page_title="Allegro IO - Code Assistant",
    page_icon="🎯",
    layout="wide"
)

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

def render_error_message(error: str):
    """Renderizza un messaggio di errore."""
    st.error(f"❌ {error}")

def render_success_message(message: str):
    """Renderizza un messaggio di successo."""
    st.success(f"✅ {message}")

def render_info_message(message: str):
    """Renderizza un messaggio informativo."""
    st.info(f"ℹ️ {message}")