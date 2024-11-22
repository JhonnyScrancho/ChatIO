"""
Configuration management for Allegro IO Code Assistant.
"""

import streamlit as st
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """
    Carica e valida la configurazione dell'applicazione.
    
    Returns:
        Dict[str, Any]: Configurazione validata
    
    Raises:
        ValueError: Se mancano secrets necessari
    """
    # Verifica secrets necessari
    required_secrets = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    for secret in required_secrets:
        if secret not in st.secrets:
            raise ValueError(f"Secret mancante: {secret}")
    
    # Configurazione predefinita
    config = {
        # API Keys
        'OPENAI_API_KEY': st.secrets['OPENAI_API_KEY'],
        'ANTHROPIC_API_KEY': st.secrets['ANTHROPIC_API_KEY'],
        
        # Limiti applicazione
        'MAX_FILE_SIZE': st.secrets.get('MAX_FILE_SIZE', 5 * 1024 * 1024),  # 5MB
        'MAX_FILES_PER_REQUEST': st.secrets.get('MAX_FILES_PER_REQUEST', 10),
        'CACHE_TTL': st.secrets.get('CACHE_TTL', 3600),  # 1 ora
        
        # Configurazione modelli
        'MODEL_CONFIG': {
            'o1-preview': {
                'token_limit': 128000,
                'cost_per_1k': {'input': 0.01, 'output': 0.03},
                'best_for': ['architecture', 'review']
            },
            'o1-mini': {
                'token_limit': 128000,
                'cost_per_1k': {'input': 0.001, 'output': 0.002},
                'best_for': ['debug', 'quick_fix']
            },
            'claude-3-5-sonnet': {
                'token_limit': 200000,
                'cost_per_1k': {'input': 0.008, 'output': 0.024},
                'best_for': ['large_files', 'documentation']
            }
        },
        
        # Configurazione UI
        'UI_CONFIG': {
            'theme_color': st.secrets.get('THEME_COLOR', '#1E88E5'),
            'max_chat_history': st.secrets.get('MAX_CHAT_HISTORY', 50),
            'code_theme': 'monokai',
            'allowed_extensions': {
                '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css',
                '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php',
                '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sh',
                '.sql', '.md', '.txt', '.json', '.yml', '.yaml'
            }
        },
        
        # Debug e logging
        'DEBUG': st.secrets.get('DEBUG', False),
        'LOG_LEVEL': st.secrets.get('LOG_LEVEL', 'INFO'),
    }
    
    return config

def get_template_config(template_name: str) -> Dict[str, Any]:
    """
    Restituisce la configurazione per un template specifico.
    
    Args:
        template_name: Nome del template
        
    Returns:
        Dict[str, Any]: Configurazione del template
    """
    templates = {
        'code_review': {
            'nome': 'Code Review',
            'modello_suggerito': 'o1-preview',
            'punti_analisi': ['Qualità', 'Pattern', 'Issues'],
            'max_files': 5
        },
        'debug': {
            'nome': 'Debug Assistant',
            'modello_suggerito': 'o1-mini',
            'punti_analisi': ['Errore', 'Soluzione', 'Prevenzione'],
            'max_files': 2
        },
        'architecture': {
            'nome': 'Architecture Analysis',
            'modello_suggerito': 'claude-3-5-sonnet',
            'punti_analisi': ['Pattern', 'SOLID', 'Improvements'],
            'max_files': 10
        }
    }
    
    return templates.get(template_name, {})

def init_app_config():
    """
    Inizializza la configurazione dell'applicazione in session_state.
    """
    if 'config' not in st.session_state:
        st.session_state.config = load_config()

def get_config(key: str, default: Any = None) -> Any:
    """
    Recupera un valore di configurazione.
    
    Args:
        key: Chiave di configurazione
        default: Valore di default se la chiave non esiste
        
    Returns:
        Any: Valore di configurazione
    """
    if 'config' not in st.session_state:
        init_app_config()
    
    return st.session_state.config.get(key, default)