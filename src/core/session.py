"""
Inizializzazione della sessione per Allegro IO Code Assistant.
"""

import os
from datetime import datetime
import streamlit as st
from typing import Dict, Any
from src.utils.cache_manager import cache_manager
from src.core.llm import LLMManager
from src.core.session import SessionManager
from src.core.files import FileManager

def initialize_session_state():
    """
    Inizializza o recupera lo stato completo della sessione.
    Include inizializzazione cache, configurazione e stato applicativo.
    """
    # 1. Inizializzazione cache manager
    if 'cache_manager' not in st.session_state:
        st.session_state.cache_manager = {
            'last_modified': datetime.now().timestamp(),
            'cache_keys': {},
            'last_clear_time': datetime.now().isoformat(),
            'stats': {
                'hits': 0,
                'misses': 0,
                'total_cached': 0
            }
        }
    
    # 2. Inizializzazione stato base
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.start_time = datetime.now().isoformat()
        st.session_state.error_log = []
        st.session_state.debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
        st.session_state.token_count = 0
        st.session_state.cost = 0.0

    # 3. Inizializzazione stato modelli e file
        if 'current_model' not in st.session_state:
            st.session_state.current_model = 'o1-mini'
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = {}
        if 'selected_file' not in st.session_state:
            st.session_state.selected_file = None
        if 'current_file' not in st.session_state:
            st.session_state.current_file = None
        
        # 4. Inizializzazione chat e messaggi
        if 'chats' not in st.session_state:
            st.session_state.chats = {
                'Chat principale': {
                    'messages': [{
                        "role": "assistant",
                        "content": "Ciao! Carica dei file e fammi delle domande su di essi. "
                                 "Posso aiutarti ad analizzarli."
                    }],
                    'created_at': datetime.now().isoformat(),
                    'settings': {
                        'model': st.session_state.current_model,
                        'temperature': 0.7,
                        'context_window': 4096
                    }
                }
            }
            st.session_state.current_chat = 'Chat principale'
        
        # 5. Inizializzazione statistiche e metriche
        if 'stats' not in st.session_state:
            st.session_state.stats = {
                'requests_total': 0,
                'tokens_total': 0,
                'cost_total': 0.0,
                'files_processed': 0,
                'chat_messages': 0,
                'errors': 0,
                'performance': {
                    'response_times': [],
                    'token_usage': [],
                    'cost_history': []
                }
            }
        
        # 6. Inizializzazione preferenze utente
        if 'user_preferences' not in st.session_state:
            st.session_state.user_preferences = {
                'theme': 'light',
                'code_theme': 'monokai',
                'font_size': 'medium',
                'show_line_numbers': True,
                'wrap_code': False,
                'auto_save': True,
                'notifications': True
            }

@cache_manager.cache_data(ttl_seconds=3600)
def initialize_clients() -> Dict[str, Any]:
    """
    Inizializza e cachea i client necessari per l'applicazione.
    Include gestione errori e logging dettagliato.
    
    Returns:
        Dict[str, Any]: Dictionary contenente i client inizializzati
    
    Raises:
        RuntimeError: Se l'inizializzazione di un client fallisce
    """
    try:
        # 1. Verifica prerequisiti
        _verify_environment()
        
        # 2. Inizializza i client principali
        clients = {
            'llm': LLMManager(),
            'session': SessionManager(),
            'file_manager': FileManager()
        }
        
        # 3. Verifica inizializzazione
        _verify_clients(clients)
        
        # 4. Aggiorna statistiche
        st.session_state.stats['initialization'] = {
            'timestamp': datetime.now().isoformat(),
            'status': 'success',
            'clients': list(clients.keys())
        }
        
        return clients
        
    except Exception as e:
        # Logging dettagliato dell'errore
        error_details = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(e).__name__,
            'error_message': str(e),
            'status': 'failed'
        }
        
        if 'error_log' not in st.session_state:
            st.session_state.error_log = []
        st.session_state.error_log.append(error_details)
        
        # Aggiorna statistiche
        st.session_state.stats['errors'] += 1
        st.session_state.stats['last_error'] = error_details
        
        raise RuntimeError(f"Errore durante l'inizializzazione dei client: {str(e)}")

def _verify_environment() -> None:
    """
    Verifica l'ambiente di esecuzione e i prerequisiti.
    
    Raises:
        ValueError: Se mancano variabili d'ambiente o dipendenze necessarie
    """
    required_env = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    missing_env = [env for env in required_env if env not in st.secrets]
    
    if missing_env:
        raise ValueError(
            f"Variabili d'ambiente mancanti: {', '.join(missing_env)}. "
            "Configurare le API keys in .streamlit/secrets.toml"
        )
    
    required_packages = ['openai', 'anthropic', 'watchdog']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        raise ValueError(
            f"Pacchetti mancanti: {', '.join(missing_packages)}. "
            "Installare i pacchetti richiesti con pip install -r requirements.txt"
        )

def _verify_clients(clients: Dict[str, Any]) -> None:
    """
    Verifica che tutti i client siano stati inizializzati correttamente.
    
    Args:
        clients: Dictionary dei client da verificare
    
    Raises:
        RuntimeError: Se un client non è stato inizializzato correttamente
    """
    required_clients = ['llm', 'session', 'file_manager']
    
    for client_name in required_clients:
        if client_name not in clients:
            raise RuntimeError(f"Client mancante: {client_name}")
        
        client = clients[client_name]
        if client is None:
            raise RuntimeError(f"Client {client_name} non inizializzato")
        
        # Verifica metodi richiesti per ogni tipo di client
        if client_name == 'llm':
            required_methods = ['process_request', 'select_model']
        elif client_name == 'session':
            required_methods = ['init_session', 'get_current_model']
        elif client_name == 'file_manager':
            required_methods = ['process_file', 'process_zip']
        
        for method in required_methods:
            if not hasattr(client, method):
                raise RuntimeError(
                    f"Client {client_name} manca del metodo richiesto: {method}"
                )

def cleanup_session():
    """
    Esegue la pulizia della sessione e libera le risorse.
    Da chiamare quando l'applicazione viene chiusa o resettata.
    """
    try:
        # 1. Salva statistiche importanti
        if 'stats' in st.session_state:
            st.session_state.stats['last_cleanup'] = datetime.now().isoformat()
        
        # 2. Pulisci le cache
        cache_manager.clear_all_caches()
        
        # 3. Chiudi le connessioni dei client
        if hasattr(st.session_state, 'clients'):
            for client in st.session_state.clients.values():
                if hasattr(client, 'cleanup'):
                    client.cleanup()
        
        # 4. Resetta lo stato della sessione
        session_keys_to_keep = {'user_preferences', 'error_log'}
        keys_to_delete = [
            key for key in st.session_state.keys()
            if key not in session_keys_to_keep
        ]
        
        for key in keys_to_delete:
            del st.session_state[key]
        
        # 5. Reinizializza lo stato base
        initialize_session_state()
        
    except Exception as e:
        # Log dell'errore ma non sollevare l'eccezione
        if 'error_log' in st.session_state:
            st.session_state.error_log.append({
                'timestamp': datetime.now().isoformat(),
                'error_type': 'cleanup_error',
                'error_message': str(e)
            })    