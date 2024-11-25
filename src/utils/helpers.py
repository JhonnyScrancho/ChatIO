"""
Utility functions for Allegro IO Code Assistant.
"""

import re
import html
from typing import List, Dict, Any, Optional
import streamlit as st

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

@st.cache_data(ttl=3600)
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
    for name, (content, lang, size) in files.items():
        total_size += size
        context.append(f"- {name}: {format_file_size(size)} ({lang})")
    
    header = f"Progetto ({format_file_size(total_size)}, {len(files)} files):"
    return header + "\n" + "\n".join(context)

@st.cache_data(ttl=60)
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
        'lines': len(lines),
        'characters': len(content),
        'functions': len(re.findall(r'def\s+\w+\s*\(', content)),
        'classes': len(re.findall(r'class\s+\w+[:\(]', content)),
        'comments': len([l for l in lines if l.strip().startswith('#')])
    }