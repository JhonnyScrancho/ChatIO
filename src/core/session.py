"""
Session management for Allegro IO Code Assistant.
Handles global state and caching through Streamlit's session state.
"""

import streamlit as st
from typing import Dict, Any, Optional

class SessionManager:
    """Gestisce lo stato globale dell'applicazione e il caching."""
    
    @staticmethod
    def init_session():
        """Inizializza o recupera lo stato della sessione."""
        if 'initialized' not in st.session_state:
            st.session_state.initialized = True
            st.session_state.chat_history = []
            st.session_state.current_model = 'o1-mini'
            st.session_state.files = {}
            st.session_state.current_file = None
            st.session_state.token_count = 0
            st.session_state.cost = 0.0
            st.session_state.last_error = None
            st.session_state.debug_mode = False
    
    @staticmethod
    def get_current_model() -> str:
        """Restituisce il modello LLM attualmente selezionato."""
        return st.session_state.current_model
    
    @staticmethod
    def set_current_model(model: str):
        """Imposta il modello LLM corrente."""
        st.session_state.current_model = model
    
    @staticmethod
    def add_to_chat_history(message: Dict[str, str]):
        """Aggiunge un messaggio alla chat history."""
        st.session_state.chat_history.append(message)
    
    @staticmethod
    def get_chat_history() -> list:
        """Restituisce la chat history completa."""
        return st.session_state.chat_history
    
    @staticmethod
    def clear_chat_history():
        """Pulisce la chat history."""
        st.session_state.chat_history = []
    
    @staticmethod
    def add_file(file_name: str, content: Any):
        """Aggiunge un file processato allo stato."""
        st.session_state.files[file_name] = content
    
    @staticmethod
    def get_file(file_name: str) -> Optional[Any]:
        """Recupera un file dallo stato."""
        return st.session_state.files.get(file_name)
    
    @staticmethod
    def get_all_files() -> Dict[str, Any]:
        """Recupera tutti i file dallo stato."""
        return st.session_state.files
    
    @staticmethod
    def set_current_file(file_name: str):
        """Imposta il file correntemente selezionato."""
        st.session_state.current_file = file_name
    
    @staticmethod
    def get_current_file() -> Optional[str]:
        """Restituisce il nome del file correntemente selezionato."""
        return st.session_state.current_file
    
    @staticmethod
    def update_token_count(tokens: int):
        """Aggiorna il conteggio dei token utilizzati."""
        st.session_state.token_count += tokens
    
    @staticmethod
    def update_cost(amount: float):
        """Aggiorna il costo totale delle richieste LLM."""
        st.session_state.cost += amount
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Restituisce le statistiche correnti della sessione."""
        return {
            'token_count': st.session_state.token_count,
            'cost': st.session_state.cost,
            'files_count': len(st.session_state.files),
            'messages_count': len(st.session_state.chat_history)
        }
    
    @staticmethod
    def set_error(error: str):
        """Imposta l'ultimo errore verificatosi."""
        st.session_state.last_error = error
    
    @staticmethod
    def get_error() -> Optional[str]:
        """Recupera l'ultimo errore."""
        return st.session_state.last_error
    
    @staticmethod
    def clear_error():
        """Pulisce l'ultimo errore."""
        st.session_state.last_error = None