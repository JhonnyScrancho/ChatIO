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
            st.session_state.token_count = 0
            st.session_state.cost = 0.0
            st.session_state.last_error = None
            st.session_state.debug_mode = False
            
            # Forum analysis specific state
            st.session_state.forum_analysis_mode = False
            st.session_state.is_forum_json = False
            st.session_state.forum_keyword = None
            st.session_state.forum_analysis_state = {
                'active': False,
                'current_analysis': None,
                'analysis_history': [],
                'last_query': None
            }
    
    @staticmethod
    def start_forum_analysis(keyword: str):
        """
        Attiva l'analisi forum.
        
        Args:
            keyword: Parola chiave estratta dal nome file
        """
        if 'forum_analysis_state' not in st.session_state:
            st.session_state.forum_analysis_state = {}
            
        st.session_state.forum_analysis_state = {
            'active': True,
            'start_time': datetime.now().isoformat(),
            'keyword': keyword,
            'current_analysis': None,
            'analysis_history': [],
            'last_query': None
        }
        
        st.session_state.forum_analysis_mode = True
    
    @staticmethod
    def stop_forum_analysis():
        """Disattiva l'analisi forum."""
        if 'forum_analysis_state' in st.session_state:
            # Salva l'analisi corrente nella storia
            if st.session_state.forum_analysis_state.get('current_analysis'):
                st.session_state.forum_analysis_state['analysis_history'].append({
                    'analysis': st.session_state.forum_analysis_state['current_analysis'],
                    'end_time': datetime.now().isoformat()
                })
            
            st.session_state.forum_analysis_state['active'] = False
            st.session_state.forum_analysis_state['current_analysis'] = None
        
        st.session_state.forum_analysis_mode = False
    
    @staticmethod
    def update_forum_analysis(analysis_data: Dict[str, Any]):
        """
        Aggiorna i dati dell'analisi forum corrente.
        
        Args:
            analysis_data: Nuovi dati dell'analisi
        """
        if 'forum_analysis_state' in st.session_state:
            st.session_state.forum_analysis_state['current_analysis'] = analysis_data
            st.session_state.forum_analysis_state['last_update'] = datetime.now().isoformat()
    
    @staticmethod
    def get_forum_analysis_state() -> Dict[str, Any]:
        """
        Recupera lo stato corrente dell'analisi forum.
        
        Returns:
            Dict[str, Any]: Stato corrente dell'analisi
        """
        return st.session_state.get('forum_analysis_state', {})
    
    @staticmethod
    def add_forum_query(query: str, results: Dict[str, Any]):
        """
        Registra una query e i suoi risultati.
        
        Args:
            query: Query eseguita
            results: Risultati della query
        """
        if 'forum_analysis_state' in st.session_state:
            st.session_state.forum_analysis_state['last_query'] = {
                'query': query,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
    
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
            'chats_count': len(st.session_state.chats)
        }
        
        # Aggiungi statistiche dell'analisi forum se attiva
        if st.session_state.get('forum_analysis_mode', False):
            forum_stats = SessionManager.get_forum_analysis_state()
            if forum_stats:
                stats['forum_analysis'] = {
                    'keyword': forum_stats.get('keyword'),
                    'active_since': forum_stats.get('start_time'),
                    'queries_count': len(forum_stats.get('analysis_history', []))
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