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
        available_models = {
            "Anthropic": ["claude-3-5-sonnet-20241022"],
            "OpenAI": ["o1-preview", "o1-mini"],
            "X.AI": ["grok-beta", "grok-vision-beta"],
            "DeepSeek": ["deepseek-chat"]
        }
        
        # Selezione del provider
        provider = st.selectbox(
            "Seleziona Provider",
            options=list(available_models.keys())
        )
        
        # Selezione del modello specifico del provider
        model = st.selectbox(
            "Seleziona Modello",
            options=available_models[provider]
        )
        
        model_descriptions = {
            "deepseek-chat": "Modello ottimizzato per programmazione con contesto fino a 64K tokens",
            "claude-3-5-sonnet-20241022": "Modello versatile con ampio contesto",
            "o1-preview": "Modello avanzato per task complessi",
            "o1-mini": "Modello leggero per task semplici",
            "grok-beta": "Modello specializzato per analisi del codice",
            "grok-vision-beta": "Modello per analisi di immagini e codice"
        }
        
        st.info(model_descriptions.get(model, ""))
        st.session_state.current_model = model