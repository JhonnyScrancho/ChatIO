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

def create_sidebar():
    with st.sidebar:
        model = st.selectbox(
            "Seleziona Modello",
            options=[
                "claude-3-5-sonnet-20241022",
                "o1-preview",
                "o1-mini",
                "grok-beta",
                "grok-vision-beta",
                "deepseek-chat"
            ],
            index=0,
            help="DeepSeek Chat: Ottimizzato per compiti di programmazione con un contesto fino a 32K tokens"
        )
        st.session_state.current_model = model