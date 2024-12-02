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
                        "content": "Ciao! Carica dei file e fammi delle domande su di essi."
                    }],
                    'created_at': datetime.now().isoformat(),
                    'analysis_mode': False,
                    'analysis_settings': {}
                }
            }
            st.session_state.current_chat = 'Chat principale'
            st.session_state.current_model = 'o1-mini'
            
            # JSON Analysis State
            st.session_state.json_analysis_mode = False
            st.session_state.json_structure = None
            st.session_state.json_type = None
            st.session_state.initial_analysis_sent = False
            
            # Analysis Cache e History
            st.session_state.analysis_cache = {}
            st.session_state.analysis_history = {}
            st.session_state.active_json_files = {}
            
            # Error handling
            st.session_state.last_error = None

    @staticmethod
    def update_analysis_state(enabled: bool, json_file: Optional[str] = None):
        """Aggiorna lo stato dell'analisi JSON."""
        st.session_state.json_analysis_mode = enabled
        if json_file:
            st.session_state.current_json_file = json_file
        if not enabled:
            st.session_state.initial_analysis_sent = False        
    
    @staticmethod
    def clear_json_analysis_cache():
        """Pulisce la cache dell'analisi."""
        st.session_state.analysis_cache = {}
        if 'current_chat' in st.session_state:
            chat_id = st.session_state.current_chat
            if chat_id in st.session_state.analysis_history:
                st.session_state.analysis_history[chat_id] = []

    @staticmethod
    def clear_json_state():
        """Pulisce tutti gli stati JSON."""
        st.session_state.json_analysis_mode = False
        st.session_state.json_structure = None
        st.session_state.json_type = None
        st.session_state.initial_analysis_sent = False
        st.session_state.analysis_cache = {}
    
    @staticmethod
    def update_json_state(structure: Dict, type: str):
        """Aggiorna lo stato JSON."""
        st.session_state.json_structure = structure
        st.session_state.json_type = type
    
    
    @staticmethod
    def update_json_file_state(filename: str, analysis: Dict[str, Any]):
        """Aggiorna lo stato per un nuovo file JSON."""
        st.session_state.active_json_files[filename] = {
            'analysis': analysis,
            'updated_at': datetime.now().isoformat()
        }
        SessionManager.clear_json_analysis_cache()

    @staticmethod
    def remove_json_file_state(filename: str):
        """Rimuove lo stato di un file JSON."""
        if filename in st.session_state.active_json_files:
            del st.session_state.active_json_files[filename]
            SessionManager.clear_json_analysis_cache()

    @staticmethod
    def toggle_json_analysis(chat_id: str, enabled: bool):
        """Gestisce il toggle dell'analisi JSON per una specifica chat."""
        if chat_id in st.session_state.chats:
            st.session_state.chats[chat_id]['analysis_mode'] = enabled
            if enabled:
                # Salva le impostazioni correnti
                st.session_state.chats[chat_id]['analysis_settings'] = {
                    'enabled_at': datetime.now().isoformat(),
                    'json_type': st.session_state.json_type,
                    'structure': st.session_state.json_structure,
                    'active_files': list(st.session_state.active_json_files.keys())
                }
            st.session_state.json_analysis_mode = enabled
            st.session_state.initial_analysis_sent = False

    @staticmethod
    def get_chat_analysis_state(chat_id: str) -> Dict[str, Any]:
        """Recupera lo stato dell'analisi per una chat specifica."""
        if chat_id in st.session_state.chats:
            chat_state = st.session_state.chats[chat_id]
            return {
                'enabled': chat_state.get('analysis_mode', False),
                'settings': chat_state.get('analysis_settings', {}),
                'history': st.session_state.analysis_history.get(chat_id, []),
                'active_files': st.session_state.active_json_files if chat_state.get('analysis_mode') else {}
            }
        return {'enabled': False, 'settings': {}, 'history': [], 'active_files': {}}

    @staticmethod
    def save_analysis_state():
        """Salva lo stato corrente dell'analisi."""
        if 'current_chat' in st.session_state:
            chat_id = st.session_state.current_chat
            st.session_state.json_analysis_states[chat_id] = {
                'mode': st.session_state.json_analysis_mode,
                'structure': st.session_state.json_structure,
                'type': st.session_state.json_type,
                'initial_analysis_sent': st.session_state.get('initial_analysis_sent', False),
                'active_files': st.session_state.active_json_files.copy()
            }

    @staticmethod
    def load_analysis_state(chat_id: str):
        """Carica lo stato dell'analisi per una chat."""
        if chat_id in st.session_state.json_analysis_states:
            state = st.session_state.json_analysis_states[chat_id]
            st.session_state.json_analysis_mode = state['mode']
            st.session_state.json_structure = state['structure']
            st.session_state.json_type = state['type']
            st.session_state.initial_analysis_sent = state['initial_analysis_sent']
            st.session_state.active_json_files = state['active_files']
    
    @staticmethod
    def add_analysis_result(chat_id: str, query: str, result: Any):
        """Aggiunge un risultato di analisi alla cronologia."""
        if chat_id not in st.session_state.analysis_history:
            st.session_state.analysis_history[chat_id] = []
        
        st.session_state.analysis_history[chat_id].append({
            'timestamp': datetime.now().isoformat(),
            'query': query,
            'result': result
        })
    
    @staticmethod
    def clear_analysis_state(chat_id: str):
        """Pulisce lo stato dell'analisi per una chat."""
        if chat_id in st.session_state.chats:
            st.session_state.chats[chat_id]['analysis_mode'] = False
            st.session_state.chats[chat_id]['analysis_settings'] = {}
        if chat_id in st.session_state.analysis_history:
            del st.session_state.analysis_history[chat_id]
        
        if st.session_state.current_chat == chat_id:
            st.session_state.json_analysis_mode = False
            st.session_state.initial_analysis_sent = False
    
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
            # Ripristina lo stato dell'analisi per la nuova chat
            chat_state = SessionManager.get_chat_analysis_state(chat_name)
            st.session_state.json_analysis_mode = chat_state['enabled']
            if chat_state['enabled']:
                st.session_state.json_structure = chat_state['settings'].get('structure')
                st.session_state.json_type = chat_state['settings'].get('json_type')
    
    @staticmethod
    def get_all_chats() -> Dict[str, Dict]:
        """Restituisce tutte le chat."""
        return st.session_state.chats
    
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
                'created_at': datetime.now().isoformat(),
                'analysis_mode': False,
                'analysis_settings': {}
            }
            st.session_state.current_chat = name
            return True
        return False
    
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
            SessionManager.clear_analysis_state(st.session_state.current_chat)
    
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
            if old_name in st.session_state.analysis_history:
                st.session_state.analysis_history[new_name] = st.session_state.analysis_history.pop(old_name)
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
            SessionManager.clear_analysis_state(name)
            del st.session_state.chats[name]
            if name in st.session_state.analysis_history:
                del st.session_state.analysis_history[name]
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
        stats = {
            'token_count': st.session_state.token_count,
            'cost': st.session_state.cost,
            'files_count': len(st.session_state.files),
            'chats_count': len(st.session_state.chats),
            'analysis_enabled': st.session_state.json_analysis_mode,
            'json_type': st.session_state.json_type
        }
        
        return stats
    
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