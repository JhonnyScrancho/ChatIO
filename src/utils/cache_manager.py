import streamlit as st
from typing import Any, Optional
from datetime import datetime
import hashlib
import logging

class CacheManager:
    """Gestisce il caching e l'invalidazione della cache per l'applicazione."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Inizializza il timestamp dell'ultima modifica
        if 'last_modified' not in st.session_state:
            st.session_state.last_modified = datetime.now().timestamp()
            
        # Inizializza il dizionario per tenere traccia delle cache keys
        if 'cache_keys' not in st.session_state:
            st.session_state.cache_keys = {}
    
    @staticmethod
    def generate_cache_key(*args, **kwargs) -> str:
        """Genera una chiave di cache univoca basata sugli argomenti."""
        # Combina tutti gli argomenti in una stringa
        key_parts = [str(arg) for arg in args]
        key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
        key_string = "|".join(key_parts)
        
        # Genera un hash SHA-256
        return hashlib.sha256(key_string.encode()).hexdigest()
    
    def clear_all_caches(self):
        """Pulisce tutte le cache di Streamlit."""
        # Pulisci la cache di st.cache_data
        st.cache_data.clear()
        
        # Pulisci la cache di st.cache_resource
        st.cache_resource.clear()
        
        # Reset del timestamp di modifica
        st.session_state.last_modified = datetime.now().timestamp()
        
        # Reset delle cache keys
        st.session_state.cache_keys = {}
        
        self.logger.info("Tutte le cache sono state pulite")
    
    def invalidate_cache_key(self, key: str):
        """Invalida una specifica chiave di cache."""
        if key in st.session_state.cache_keys:
            del st.session_state.cache_keys[key]
            self.logger.info(f"Cache key {key} invalidata")
    
    def cache_data(self, ttl_seconds: Optional[int] = None):
        """
        Decoratore personalizzato per il caching dei dati con gestione dell'invalidazione.
        
        Args:
            ttl_seconds: Tempo di vita della cache in secondi
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                # Genera una chiave di cache per questa chiamata
                cache_key = self.generate_cache_key(func.__name__, *args, **kwargs)
                
                # Verifica se il dato è in cache e se è ancora valido
                cached_data = st.session_state.cache_keys.get(cache_key)
                
                if cached_data is not None:
                    timestamp, data = cached_data
                    
                    # Verifica TTL se specificato
                    if ttl_seconds is not None:
                        current_time = datetime.now().timestamp()
                        if current_time - timestamp <= ttl_seconds:
                            return data
                    else:
                        return data
                
                # Se non in cache o cache invalida, esegui la funzione
                result = func(*args, **kwargs)
                
                # Salva il risultato in cache
                st.session_state.cache_keys[cache_key] = (
                    datetime.now().timestamp(),
                    result
                )
                
                return result
            return wrapper
        return decorator
    
    def watch_file_changes(self, filepath: str):
        """
        Monitora i cambiamenti di un file e invalida la cache se necessario.
        
        Args:
            filepath: Percorso del file da monitorare
        """
        try:
            import os
            current_mtime = os.path.getmtime(filepath)
            
            # Verifica se il file è stato modificato
            if current_mtime > st.session_state.last_modified:
                self.logger.info(f"Rilevata modifica del file: {filepath}")
                self.clear_all_caches()
                st.experimental_rerun()
                
        except Exception as e:
            self.logger.error(f"Errore nel monitoraggio del file {filepath}: {e}")

# Esempio di utilizzo nel codice principale
cache_manager = CacheManager()

# Decoratore per le funzioni che necessitano di caching
@cache_manager.cache_data(ttl_seconds=300)  # 5 minuti di TTL
def process_data(data: Any) -> Any:
    # Elaborazione costosa
    return processed_result

# Aggiungere questo nel main loop dell'applicazione
def setup_file_monitoring():
    """Configura il monitoraggio dei file per il ricaricamento automatico."""
    import os
    
    # Lista dei file da monitorare
    files_to_watch = [
        'main.py',
        'src/core/llm.py',
        'src/core/files.py',
        'src/core/session.py',
        'src/ui/components.py',
        'src/ui/layout.py'
    ]
    
    for file in files_to_watch:
        if os.path.exists(file):
            cache_manager.watch_file_changes(file)

# Nel main.py, aggiungere:
if __name__ == "__main__":
    setup_file_monitoring()
    main()