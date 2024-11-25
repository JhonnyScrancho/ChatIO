"""
Gestione delle sessioni per Allegro IO Code Assistant.
Gestisce lo stato globale e il caching attraverso Streamlit session state.
"""

import streamlit as st
from typing import Dict, Any, Optional, List
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
            st.session_state.current_model = 'o1-mini'  # Modello di default
            st.session_state.files = {}
            st.session_state.current_file = None
            st.session_state.selected_file = None       # Per il file viewer
            st.session_state.token_count = 0
            st.session_state.cost = 0.0
            st.session_state.last_error = None
            st.session_state.debug_mode = False
            st.session_state.start_time = datetime.now().isoformat()
            st.session_state.uploaded_files = {}
    
    @staticmethod
    def get_current_model() -> str:
        """Restituisce il modello LLM attualmente selezionato."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        return st.session_state.current_model
    
    @staticmethod
    def set_current_model(model: str):
        """Imposta il modello LLM corrente."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        st.session_state.current_model = model
    
    @staticmethod
    def get_current_chat() -> Dict:
        """Restituisce la chat corrente."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        return st.session_state.chats[st.session_state.current_chat]
    
    @staticmethod
    def set_current_chat(chat_name: str):
        """Imposta la chat corrente."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        if chat_name in st.session_state.chats:
            st.session_state.current_chat = chat_name
    
    @staticmethod
    def get_all_chats() -> Dict[str, Dict]:
        """Restituisce tutte le chat."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        return st.session_state.chats
    
    @staticmethod
    def add_message_to_current_chat(message: Dict[str, str]):
        """Aggiunge un messaggio alla chat corrente."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        st.session_state.chats[st.session_state.current_chat]['messages'].append(message)
    
    @staticmethod
    def get_messages_from_current_chat() -> List[Dict[str, str]]:
        """Restituisce i messaggi della chat corrente."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        return st.session_state.chats[st.session_state.current_chat]['messages']
    
    @staticmethod
    def clear_current_chat():
        """Pulisce i messaggi della chat corrente."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        if st.session_state.current_chat in st.session_state.chats:
            st.session_state.chats[st.session_state.current_chat]['messages'] = []
    
    @staticmethod
    def create_new_chat(name: str) -> bool:
        """Crea una nuova chat."""
        SessionManager.init_session()  # Assicura l'inizializzazione
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
        SessionManager.init_session()  # Assicura l'inizializzazione
        if old_name in st.session_state.chats and new_name not in st.session_state.chats:
            st.session_state.chats[new_name] = st.session_state.chats.pop(old_name)
            if st.session_state.current_chat == old_name:
                st.session_state.current_chat = new_name
            return True
        return False
    
    @staticmethod
    def delete_chat(name: str) -> bool:
        """Elimina una chat esistente."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        if name in st.session_state.chats and len(st.session_state.chats) > 1:
            del st.session_state.chats[name]
            if st.session_state.current_chat == name:
                st.session_state.current_chat = list(st.session_state.chats.keys())[0]
            return True
        return False
    
    @staticmethod
    def add_file(file_name: str, content: Any):
        """Aggiunge un file processato allo stato."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        st.session_state.files[file_name] = content
    
    @staticmethod
    def get_file(file_name: str) -> Optional[Any]:
        """Recupera un file dallo stato."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        return st.session_state.files.get(file_name)
    
    @staticmethod
    def get_all_files() -> Dict[str, Any]:
        """Recupera tutti i file dallo stato."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        return st.session_state.files
    
    @staticmethod
    def set_current_file(file_name: str):
        """Imposta il file correntemente selezionato."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        st.session_state.current_file = file_name
    
    @staticmethod
    def get_current_file() -> Optional[str]:
        """Restituisce il nome del file correntemente selezionato."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        return st.session_state.current_file
    
    @staticmethod
    def update_token_count(tokens: int):
        """Aggiorna il conteggio dei token utilizzati."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        st.session_state.token_count += tokens
    
    @staticmethod
    def update_cost(amount: float):
        """Aggiorna il costo totale delle richieste LLM."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        st.session_state.cost += amount
    
    @staticmethod
    def get_stats() -> Dict[str, Any]:
        """Restituisce le statistiche correnti della sessione."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        return {
            'token_count': st.session_state.token_count,
            'cost': st.session_state.cost,
            'files_count': len(st.session_state.files),
            'chats_count': len(st.session_state.chats)
        }
    
    @staticmethod
    def set_error(error: str):
        """Imposta l'ultimo errore verificatosi."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        st.session_state.last_error = error
    
    @staticmethod
    def get_error() -> Optional[str]:
        """Recupera l'ultimo errore."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        return st.session_state.last_error
    
    @staticmethod
    def clear_error():
        """Pulisce l'ultimo errore."""
        SessionManager.init_session()  # Assicura l'inizializzazione
        st.session_state.last_error = None
    
    @staticmethod
    def reset_session():
        """Resetta completamente la sessione."""
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        SessionManager.init_session()
    
    @staticmethod
    def export_session_data() -> Dict[str, Any]:
        """
        Esporta tutti i dati della sessione per backup.
        
        Returns:
            Dict[str, Any]: Dati completi della sessione
        """
        SessionManager.init_session()
        return {
            'chats': st.session_state.chats,
            'files': st.session_state.files,
            'stats': SessionManager.get_stats(),
            'current_model': st.session_state.current_model,
            'current_chat': st.session_state.current_chat,
            'current_file': st.session_state.current_file,
            'start_time': st.session_state.start_time
        }
    
    @staticmethod
    def import_session_data(data: Dict[str, Any]) -> bool:
        """
        Importa dati di sessione da un backup.
        
        Args:
            data: Dati della sessione da importare
            
        Returns:
            bool: True se l'importazione è riuscita
        """
        try:
            SessionManager.reset_session()
            st.session_state.chats = data['chats']
            st.session_state.files = data['files']
            st.session_state.current_model = data['current_model']
            st.session_state.current_chat = data['current_chat']
            st.session_state.current_file = data['current_file']
            st.session_state.start_time = data['start_time']
            return True
        except Exception as e:
            SessionManager.set_error(f"Errore nell'importazione: {str(e)}")
            return False