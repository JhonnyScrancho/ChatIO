"""
Funzioni di utilità per Allegro IO Code Assistant.
"""

import re
import html
from typing import List, Dict, Any, Optional
import streamlit as st
from src.utils.cache_manager import cache_manager

def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Tronca il testo alla lunghezza specificata.
    
    Args:
        text: Testo da troncare
        max_length: Lunghezza massima
        
    Returns:
        str: Testo troncato
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def calculate_tokens(text: str) -> int:
    """
    Calcola approssimativamente il numero di token in un testo.
    Approssimazione semplice: 1 token ~= 4 caratteri.
    
    Args:
        text: Testo da analizzare
        
    Returns:
        int: Numero approssimativo di token
    """
    return len(text) // 4

def sanitize_input(text: str) -> str:
    """
    Sanitizza l'input dell'utente.
    
    Args:
        text: Testo da sanitizzare
        
    Returns:
        str: Testo sanitizzato
    """
    # Rimuove tag HTML
    text = re.sub(r'<[^>]+>', '', text)
    # Codifica caratteri speciali
    text = html.escape(text)
    return text

@cache_manager.cache_data(ttl_seconds=3600)
def estimate_request_cost(model: str, text_length: int) -> float:
    """
    Stima il costo di una richiesta LLM.
    
    Args:
        model: Nome del modello
        text_length: Lunghezza del testo
        
    Returns:
        float: Costo stimato in USD
    """
    tokens = calculate_tokens(text_length)
    
    # Assicura che la configurazione esista in session state
    if 'config' not in st.session_state:
        from src.utils.config import load_config
        st.session_state.config = load_config()
    
    cost_map = st.session_state.config['MODEL_CONFIG'][model]['cost_per_1k']
    
    # Stima 40% input, 60% output
    input_cost = (tokens * 0.4 * cost_map['input']) / 1000
    output_cost = (tokens * 0.6 * cost_map['output']) / 1000
    
    return round(input_cost + output_cost, 4)

def format_file_size(size_bytes: int) -> str:
    """
    Formatta una dimensione in bytes in formato leggibile.
    
    Args:
        size_bytes: Dimensione in bytes
        
    Returns:
        str: Dimensione formattata
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} GB"

@cache_manager.cache_data(ttl_seconds=60)
def parse_code_context(files: Dict[str, Any]) -> str:
    """
    Genera un contesto leggibile dai file di codice.
    
    Args:
        files: Dizionario dei file
        
    Returns:
        str: Contesto formattato
    """
    context = []
    total_size = 0
    
    for name, info in files.items():
        size = info.get('size', 0)
        lang = info.get('language', 'text')
        total_size += size
        context.append(f"- {name}: {format_file_size(size)} ({lang})")
    
    header = f"Progetto ({format_file_size(total_size)}, {len(files)} file):"
    return header + "\n" + "\n".join(context)

@cache_manager.cache_data(ttl_seconds=60)
def analyze_code_complexity(content: str) -> Dict[str, Any]:
    """
    Analisi base della complessità del codice.
    
    Args:
        content: Contenuto del file
        
    Returns:
        Dict[str, Any]: Metriche di complessità
    """
    lines = content.split('\n')
    return {
        'righe': len(lines),
        'caratteri': len(content),
        'funzioni': len(re.findall(r'def\s+\w+\s*\(', content)),
        'classi': len(re.findall(r'class\s+\w+[:\(]', content)),
        'commenti': len([l for l in lines if l.strip().startswith('#')]),
        'righe_vuote': len([l for l in lines if not l.strip()]),
        'complessita': {
            'nesting_max': max(
                (len(re.findall(r'^[ \t]+', l)) for l in lines if l.strip()),
                default=0
            ) // 4,
            'lunghezza_media_riga': sum(len(l) for l in lines) / len(lines) if lines else 0
        }
    }

def validate_file_content(content: str, file_type: str) -> bool:
    """
    Valida il contenuto di un file in base al suo tipo.
    
    Args:
        content: Contenuto del file
        file_type: Tipo/estensione del file
        
    Returns:
        bool: True se il contenuto è valido
    """
    if not content:
        return False
        
    # Validazione per tipo di file
    validators = {
        'py': lambda x: 'import' in x or 'def ' in x or 'class ' in x,
        'js': lambda x: 'function' in x or 'const' in x or 'let' in x or 'var' in x,
        'html': lambda x: '<html' in x.lower() or '<body' in x.lower(),
        'css': lambda x: '{' in x and '}' in x and ':' in x,
        'json': lambda x: (x.strip().startswith('{') and x.strip().endswith('}')) or 
                         (x.strip().startswith('[') and x.strip().endswith(']'))
    }
    
    validator = validators.get(file_type.lower().lstrip('.'))
    return validator(content) if validator else True