"""
Gestione della cache per Allegro IO Code Assistant.
Implementa un sistema di caching con TTL e invalidazione.
"""

import streamlit as st
from typing import Any, Optional, Callable
from datetime import datetime
import hashlib
import logging
from functools import wraps

class CacheManager:
    """Gestisce il caching e l'invalidazione della cache per l'applicazione."""
    
    def __init__(self):
        """Inizializza il CacheManager."""
        self.logger = logging.getLogger(__name__)
        self._initialize_state()
    
    def _initialize_state(self):
        """Inizializza lo stato della sessione per il caching."""
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
    
    @staticmethod
    def generate_cache_key(*args, **kwargs) -> str:
        """
        Genera una chiave di cache univoca basata sugli argomenti.
        
        Args:
            *args: Argomenti posizionali
            **kwargs: Argomenti nominali
            
        Returns:
            str: Chiave hash univoca
        """
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def clear_all_caches(self):
        """Pulisce tutte le cache dell'applicazione."""
        self._initialize_state()
        st.cache_data.clear()
        st.cache_resource.clear()
        st.session_state.cache_manager['last_modified'] = datetime.now().timestamp()
        st.session_state.cache_manager['cache_keys'] = {}
        st.session_state.cache_manager['last_clear_time'] = datetime.now().isoformat()
        st.session_state.cache_manager['stats'] = {
            'hits': 0,
            'misses': 0,
            'total_cached': 0
        }
        self.logger.info("Cache pulita completamente")
    
    def invalidate_cache_key(self, key: str):
        """
        Invalida una specifica chiave di cache.
        
        Args:
            key: Chiave da invalidare
        """
        self._initialize_state()
        if key in st.session_state.cache_manager['cache_keys']:
            del st.session_state.cache_manager['cache_keys'][key]
            self.logger.info(f"Cache key '{key}' invalidata")
    
    def cache_data(self, ttl_seconds: Optional[int] = None) -> Callable:
        """
        Decoratore per il caching dei dati con TTL.
        
        Args:
            ttl_seconds: Tempo di vita della cache in secondi
            
        Returns:
            Callable: Funzione decorata
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                self._initialize_state()
                
                # Genera chiave cache
                cache_key = self.generate_cache_key(func.__name__, *args, **kwargs)
                
                # Verifica cache
                cache_data = st.session_state.cache_manager['cache_keys'].get(cache_key)
                if cache_data is not None:
                    timestamp, data = cache_data
                    current_time = datetime.now().timestamp()
                    
                    # Verifica TTL
                    if ttl_seconds is None or (current_time - timestamp) <= ttl_seconds:
                        st.session_state.cache_manager['stats']['hits'] += 1
                        return data
                
                # Esegue la funzione e cachea il risultato
                st.session_state.cache_manager['stats']['misses'] += 1
                result = func(*args, **kwargs)
                
                st.session_state.cache_manager['cache_keys'][cache_key] = (
                    datetime.now().timestamp(),
                    result
                )
                st.session_state.cache_manager['stats']['total_cached'] += 1
                
                return result
            
            return wrapper
        return decorator
    
    def get_cache_info(self) -> dict:
        """
        Restituisce informazioni sullo stato attuale della cache.
        
        Returns:
            dict: Statistiche e informazioni sulla cache
        """
        self._initialize_state()
        stats = st.session_state.cache_manager['stats']
        total_requests = stats['hits'] + stats['misses']
        hit_ratio = (stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'ultimo_aggiornamento': datetime.fromtimestamp(
                st.session_state.cache_manager['last_modified']
            ).isoformat(),
            'chiavi_cache': len(st.session_state.cache_manager['cache_keys']),
            'ultima_pulizia': st.session_state.cache_manager['last_clear_time'],
            'statistiche': {
                'hit_ratio': f"{hit_ratio:.1f}%",
                'cache_hits': stats['hits'],
                'cache_misses': stats['misses'],
                'elementi_cachati': stats['total_cached']
            }
        }
    
    def get_last_clear_time(self) -> str:
        """
        Restituisce il timestamp dell'ultima pulizia della cache.
        
        Returns:
            str: Data e ora dell'ultima pulizia
        """
        self._initialize_state()
        return st.session_state.cache_manager['last_clear_time']
    
    def monitor_performance(self):
        """Monitora le performance della cache."""
        stats = st.session_state.cache_manager['stats']
        total_requests = stats['hits'] + stats['misses']
        
        if total_requests > 1000:  # Monitora solo con un numero significativo di richieste
            hit_ratio = stats['hits'] / total_requests
            if hit_ratio < 0.5:  # Hit ratio sotto il 50%
                self.logger.warning(
                    f"Performance cache basse: hit ratio {hit_ratio:.1%}. "
                    "Considerare l'aumento del TTL o la revisione della strategia di caching."
                )

# Istanza singleton del CacheManager
cache_manager = CacheManager()