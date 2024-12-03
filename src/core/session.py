"""
Session management for Allegro IO Code Assistant.
Handles global state and caching through Streamlit's session state.
"""

import streamlit as st
from typing import Dict, Any, Optional
from datetime import datetime

class SessionManager:
    """Gestisce lo stato globale dell'applicazione e il caching."""
    
    @staticmethod
    def init_session():
        """Inizializza o recupera lo stato della sessione."""
        if 'initialized' not in st.session_state:
            st.session_state.initialized = True
            st.session_state.chats = {
                'Chat principale': {
                    'messages': [{
                        "role": "assistant",
                        "content": "Ciao! Carica dei file e fammi delle domande su di essi. Posso aiutarti ad analizzarli."
                    }],
                    'created_at': datetime.now().isoformat()
                }
            }
            st.session_state.current_chat = 'Chat principale'
            st.session_state.current_model = 'o1-mini'
            st.session_state.files = {}
            st.session_state.current_file = None
            # Track API usage
            st.session_state.api_usage = {
                'openai': {'total_tokens': 0, 'total_cost': 0.0},
                'anthropic': {'total_tokens': 0, 'total_cost': 0.0}
            }
    
    @staticmethod
    def update_api_usage(provider: str, tokens: int, cost: float):
        """Aggiorna l'utilizzo delle API."""
        if provider in st.session_state.api_usage:
            st.session_state.api_usage[provider]['total_tokens'] += tokens
            st.session_state.api_usage[provider]['total_cost'] += cost
    
    @staticmethod
    def get_total_usage():
        """Restituisce l'utilizzo totale delle API."""
        total_tokens = sum(provider['total_tokens'] for provider in st.session_state.api_usage.values())
        total_cost = sum(provider['total_cost'] for provider in st.session_state.api_usage.values())
        return total_tokens, total_cost
    
    @staticmethod
    def get_current_model() -> str:
        """Restituisce il modello LLM attualmente selezionato."""
        return st.session_state.get('current_model', 'o1-mini')
    
    @staticmethod
    def set_current_model(model: str):
        """Imposta il modello LLM corrente."""
        st.session_state.current_model = model
    
    @staticmethod
    def get_current_chat() -> Dict:
        """Restituisce la chat corrente."""
        return st.session_state.chats[st.session_state.current_chat]
    
    @staticmethod
    def set_current_chat(chat_name: str):
        """Imposta la chat corrente."""
        if chat_name in st.session_state.chats:
            st.session_state.current_chat = chat_name
    
    @staticmethod
    def get_all_chats() -> Dict[str, Dict]:
        """Restituisce tutte le chat."""
        return st.session_state.chats
    
    @staticmethod
    def add_message_to_current_chat(message: Dict[str, str]):
        """Aggiunge un messaggio alla chat corrente."""
        if 'chats' not in st.session_state or st.session_state.current_chat not in st.session_state.chats:
            SessionManager.init_session()
        st.session_state.chats[st.session_state.current_chat]['messages'].append(message)
    
    @staticmethod
    def get_messages_from_current_chat() -> list:
        """Restituisce i messaggi della chat corrente."""
        if 'chats' not in st.session_state or st.session_state.current_chat not in st.session_state.chats:
            SessionManager.init_session()
        return st.session_state.chats[st.session_state.current_chat]['messages']
    
    @staticmethod
    def clear_current_chat():
        """Pulisce i messaggi della chat corrente."""
        if 'chats' in st.session_state and st.session_state.current_chat in st.session_state.chats:
            st.session_state.chats[st.session_state.current_chat]['messages'] = []
    
    @staticmethod
    def create_new_chat(name: str) -> bool:
        """
        Crea una nuova chat.
        
        Args:
            name: Nome della nuova chat
            
        Returns:
            bool: True se la chat è stata creata, False se esiste già
        """
        if name not in st.session_state.chats:
            st.session_state.chats[name] = {
                'messages': [],
                'created_at': datetime.now().isoformat()
            }
            st.session_state.current_chat = name
            return True
        return False
    
    @staticmethod
    def rename_chat(old_name: str, new_name: str) -> bool:
        """
        Rinomina una chat esistente.
        
        Args:
            old_name: Nome attuale della chat
            new_name: Nuovo nome della chat
            
        Returns:
            bool: True se la chat è stata rinominata, False se non è possibile
        """
        if old_name in st.session_state.chats and new_name not in st.session_state.chats:
            st.session_state.chats[new_name] = st.session_state.chats.pop(old_name)
            if st.session_state.current_chat == old_name:
                st.session_state.current_chat = new_name
            return True
        return False
    
    @staticmethod
    def delete_chat(name: str) -> bool:
        """
        Elimina una chat esistente.
        
        Args:
            name: Nome della chat da eliminare
            
        Returns:
            bool: True se la chat è stata eliminata, False se non è possibile
        """
        if name in st.session_state.chats and len(st.session_state.chats) > 1:
            del st.session_state.chats[name]
            if st.session_state.current_chat == name:
                st.session_state.current_chat = list(st.session_state.chats.keys())[0]
            return True
        return False
    
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
    def get_stats() -> Dict[str, Any]:
        """Restituisce le statistiche correnti della sessione."""
        return {
            'token_count': st.session_state.token_count,
            'cost': st.session_state.cost,
            'files_count': len(st.session_state.files),
            'chats_count': len(st.session_state.chats)
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