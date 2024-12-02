"""
Gestione della cache per Allegro IO Code Assistant.
Implementa un sistema di caching con TTL e invalidazione.
"""

import time
import types
import pandas as pd
import numpy as np
from typing import Any, Dict, Optional, Callable, List
from datetime import datetime
import hashlib
import logging
from functools import wraps
import streamlit as st
from core.data_analysis import DataAnalysisManager

class CacheManager:
    """Gestisce il caching e l'invalidazione della cache per l'applicazione."""
    
    def __init__(self):
        """Inizializza il CacheManager."""
        self.logger = logging.getLogger(__name__)
        self._initialize_state()
        self.cache = {}
        self.ttl = 3600  # 1 ora di default
        self.max_size = 1000  # Numero massimo di entry in cache
    
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
    
    def _generate_cache_key(self, query: str, data_type: str, context: Dict) -> str:
        """Genera una chiave di cache univoca."""
        key_components = [
            query,
            data_type,
            context.get('structure', {}),
            context.get('timestamp', '')
        ]
        return hashlib.md5(str(key_components).encode()).hexdigest()

    def get(self, query: str, data_type: str, context: Dict) -> Optional[Any]:
        """Recupera un risultato dalla cache."""
        key = self._generate_cache_key(query, data_type, context)
        if key in self.cache:
            entry = self.cache[key]
            if time.time() - entry['timestamp'] < self.ttl:
                return entry['result']
            else:
                del self.cache[key]
        return None

    def set(self, query: str, data_type: str, context: Dict, result: Any):
        """Salva un risultato in cache."""
        if len(self.cache) >= self.max_size:
            # Rimuovi le entry più vecchie
            oldest = sorted(self.cache.items(), key=lambda x: x[1]['timestamp'])[0][0]
            del self.cache[oldest]
        
        key = self._generate_cache_key(query, data_type, context)
        self.cache[key] = {
            'timestamp': time.time(),
            'result': result
        }
    
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

def process_chunk(chunk: List[Any]) -> Dict[str, Any]:
    """
    Processa un chunk di dati.
    
    Args:
        chunk: Lista di dati da processare
        
    Returns:
        Dict[str, Any]: Risultati dell'analisi del chunk
    """
    result = {
        'statistics': {},
        'aggregations': {},
        'patterns': {}
    }
    
    if not chunk:
        return result
        
    # Converti in DataFrame per analisi
    try:
        df = pd.DataFrame(chunk)
        
        # Statistiche base
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        result['statistics'] = {
            'count': len(df),
            'numeric_stats': {
                col: {
                    'mean': df[col].mean(),
                    'std': df[col].std(),
                    'min': df[col].min(),
                    'max': df[col].max()
                } for col in numeric_cols
            }
        }
        
        # Aggregazioni
        if numeric_cols.any():
            result['aggregations'] = {
                'sum': df[numeric_cols].sum().to_dict(),
                'median': df[numeric_cols].median().to_dict()
            }
        
        # Pattern di base
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        result['patterns'] = {
            col: df[col].value_counts().head(5).to_dict()
            for col in categorical_cols
        }
        
    except Exception as e:
        logging.error(f"Errore nel processare chunk: {str(e)}")
        result['error'] = str(e)
    
    return result

def combine_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Combina i risultati dell'analisi di più chunk.
    
    Args:
        results: Lista di risultati da combinare
        
    Returns:
        Dict[str, Any]: Risultati combinati
    """
    if not results:
        return {}
        
    combined = {
        'statistics': {
            'count': 0,
            'numeric_stats': {}
        },
        'aggregations': {
            'sum': {},
            'median': []
        },
        'patterns': {}
    }
    
    try:
        # Combina statistiche
        for result in results:
            stats = result.get('statistics', {})
            combined['statistics']['count'] += stats.get('count', 0)
            
            for col, values in stats.get('numeric_stats', {}).items():
                if col not in combined['statistics']['numeric_stats']:
                    combined['statistics']['numeric_stats'][col] = {
                        'mean': [],
                        'std': [],
                        'min': float('inf'),
                        'max': float('-inf')
                    }
                
                curr_stats = combined['statistics']['numeric_stats'][col]
                curr_stats['mean'].append(values['mean'])
                curr_stats['std'].append(values['std'])
                curr_stats['min'] = min(curr_stats['min'], values['min'])
                curr_stats['max'] = max(curr_stats['max'], values['max'])
        
        # Finalizza statistiche
        for col in combined['statistics']['numeric_stats']:
            stats = combined['statistics']['numeric_stats'][col]
            stats['mean'] = np.mean(stats['mean'])
            stats['std'] = np.sqrt(np.mean(np.square(stats['std'])))
        
        # Combina aggregazioni
        for result in results:
            aggs = result.get('aggregations', {})
            for col, value in aggs.get('sum', {}).items():
                combined['aggregations']['sum'][col] = combined['aggregations']['sum'].get(col, 0) + value
            combined['aggregations']['median'].extend([
                aggs.get('median', {}).get(col, [])
                for col in aggs.get('median', {})
            ])
        
        # Finalizza mediane
        if combined['aggregations']['median']:
            combined['aggregations']['median'] = np.median(combined['aggregations']['median'])
        
        # Combina patterns
        for result in results:
            for col, patterns in result.get('patterns', {}).items():
                if col not in combined['patterns']:
                    combined['patterns'][col] = {}
                for value, count in patterns.items():
                    combined['patterns'][col][value] = combined['patterns'][col].get(value, 0) + count
        
    except Exception as e:
        logging.error(f"Errore nel combinare risultati: {str(e)}")
        combined['error'] = str(e)
    
    return combined

class ErrorHandler:
    """Gestisce gli errori in modo centralizzato."""
    
    @staticmethod
    def handle_analysis_error(error: Exception, context: Dict) -> str:
        """Gestisce errori di analisi."""
        error_type = type(error).__name__
        
        if error_type == 'JSONDecodeError':
            return "❌ Il JSON fornito non è valido. Verifica la formattazione."
        elif error_type == 'KeyError':
            return "❌ Campo richiesto non trovato nei dati."
        elif error_type == 'ValueError':
            return f"❌ Errore di valore: {str(error)}"
        elif error_type == 'MemoryError':
            return "❌ Dataset troppo grande per l'analisi."
        else:
            logging.error(f"Analysis error: {str(error)}", exc_info=True, extra=context)
            return "❌ Si è verificato un errore durante l'analisi. Riprova più tardi."

    @staticmethod
    def handle_query_error(error: Exception, query: str) -> str:
        """Gestisce errori nelle query."""
        if "syntax error" in str(error).lower():
            return "❌ La query non è formulata correttamente."
        elif "ambiguous" in str(error).lower():
            return "❌ La richiesta è ambigua. Puoi essere più specifico?"
        else:
            logging.error(f"Query error for '{query}': {str(error)}", exc_info=True)
            return "❌ Non sono riuscito a processare la richiesta. Prova a riformularla."

class PerformanceOptimizer:
    """Ottimizza le performance delle analisi."""
    
    @staticmethod
    def optimize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """Ottimizza un DataFrame per l'analisi."""
        # Converti tipi di dati per ottimizzare memoria
        for col in df.columns:
            if df[col].dtype == 'object':
                if df[col].nunique() / len(df) < 0.5:  # Se colonna ha bassa cardinalità
                    df[col] = df[col].astype('category')
            elif df[col].dtype == 'float64':
                if df[col].apply(lambda x: x.is_integer()).all():
                    df[col] = df[col].astype('int32')
                else:
                    df[col] = df[col].astype('float32')
        return df

    @staticmethod
    def chunk_analysis(data: List[Any], chunk_size: int = 1000) -> Dict[str, Any]:
        """
        Analizza dati in chunks per gestire grandi dataset.
        
        Args:
            data: Lista di dati da analizzare
            chunk_size: Dimensione di ogni chunk
            
        Returns:
            Dict[str, Any]: Risultati combinati dell'analisi
        """
        results = []
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            chunk_result = process_chunk(chunk)
            results.append(chunk_result)
        return combine_results(results)

def apply_optimizations(data_analysis_manager: DataAnalysisManager):
    """
    Applica ottimizzazioni al DataAnalysisManager.
    
    Args:
        data_analysis_manager: Istanza di DataAnalysisManager da ottimizzare
    """
    # Aggiungi cache manager
    data_analysis_manager.cache_manager = CacheManager()
    
    # Aggiungi error handler
    data_analysis_manager.error_handler = ErrorHandler()
    
    # Aggiungi performance optimizer
    data_analysis_manager.performance_optimizer = PerformanceOptimizer()
    
    # Decora metodi con ottimizzazioni
    original_query_data = data_analysis_manager.query_data
    
    def optimized_query_data(self, query: str) -> str:
        """
        Versione ottimizzata del metodo query_data.
        
        Args:
            query: Query da processare
            
        Returns:
            str: Risultato dell'analisi
        """
        try:
            # Check cache
            context = {
                'structure': st.session_state.json_structure,
                'timestamp': datetime.now().isoformat()
            }
            cached_result = self.cache_manager.get(query, st.session_state.json_type, context)
            if cached_result:
                return cached_result
            
            # Optimize data if needed
            if isinstance(self.current_dataset, pd.DataFrame):
                self.current_dataset = self.performance_optimizer.optimize_dataframe(
                    self.current_dataset
                )
            
            # Se il dataset è grande, usa chunk analysis
            if len(self.current_dataset) > 10000:
                result = self.performance_optimizer.chunk_analysis(
                    self.current_dataset.to_dict('records'),
                    chunk_size=5000
                )
            else:
                # Execute query normalmente
                result = original_query_data(self, query)
            
            # Cache result
            self.cache_manager.set(query, st.session_state.json_type, context, result)
            
            return result
            
        except Exception as e:
            return self.error_handler.handle_query_error(e, query)
    
    # Applica il metodo ottimizzato
    data_analysis_manager.query_data = types.MethodType(optimized_query_data, data_analysis_manager)