"""
Main layout management for Allegro IO Code Assistant.
"""

from src.ui.components import FileExplorer, ChatInterface, CodeViewer, ModelSelector, StatsDisplay
import streamlit as st

def render_error_message(error: str):
    """Renderizza un messaggio di errore."""
    st.error(f"❌ {error}")

def render_success_message(message: str):
    """Renderizza un messaggio di successo."""
    st.success(f"✅ {message}")

def render_info_message(message: str):
    """Renderizza un messaggio informativo."""
    st.info(f"ℹ️ {message}")

def render_main_layout():
    """
    Renderizza il layout principale dell'applicazione.
    Include il setup della pagina, sidebar e area principale.
    """
    st.set_page_config(page_title="Allegro IO", page_icon="👲🏿", layout="wide")
    
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

# Esporta le funzioni necessarie
__all__ = [
    'render_main_layout',
    'render_error_message',
    'render_success_message',
    'render_info_message'
]