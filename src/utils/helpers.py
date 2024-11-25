"""
Utility functions for Allegro IO Code Assistant.
"""

import re
import html
from typing import List, Dict, Any, Optional, Union
import streamlit as st

class TokenCounter:
    """Accurate token counter for LLM inputs."""
    
    # Common word boundaries and special characters that often denote token breaks
    TOKEN_PATTERNS = [
        r'\b\w+\b',  # Words
        r'[^\w\s]+',  # Punctuation and special characters
        r'\s+',       # Whitespace
        r'\d+',       # Numbers
        r'[A-Z][a-z]+', # CamelCase splits
        r'[a-z0-9]+(?:[A-Z][a-z0-9]+)*', # camelCase splits
        r'[A-Z0-9]+(?:[A-Z][a-z0-9]+)*', # PascalCase splits
        r'[a-zA-Z0-9]+(_[a-zA-Z0-9]+)+', # snake_case splits
        r'[a-zA-Z0-9]+(-[a-zA-Z0-9]+)+', # kebab-case splits
    ]
    
    # Common programming tokens that should be counted as single tokens
    PROGRAMMING_TOKENS = {
        'keywords': {'def', 'class', 'import', 'from', 'return', 'if', 'else', 'elif',
                    'try', 'except', 'finally', 'for', 'while', 'break', 'continue',
                    'pass', 'raise', 'with', 'as', 'in', 'is', 'not', 'and', 'or'},
        'operators': {'=', '==', '!=', '>', '<', '>=', '<=', '+', '-', '*', '/',
                     '+=', '-=', '*=', '/=', '%=', '**', '//', '&', '|', '^', '~',
                     '>>', '<<'},
        'brackets': {'{', '}', '[', ']', '(', ')'},
        'special': {'self', 'None', 'True', 'False', '__init__', '__main__',
                   'async', 'await'}
    }
    
    @staticmethod
    @st.cache_data
    def count_tokens(text: Union[str, Dict, List]) -> int:
        """
        Count tokens accurately for different input types.
        
        Args:
            text: Input text, dictionary, or list to count tokens for
            
        Returns:
            int: Estimated token count
        """
        if isinstance(text, dict):
            return sum(TokenCounter.count_tokens(v) for v in text.values())
        elif isinstance(text, list):
            return sum(TokenCounter.count_tokens(item) for item in text)
        elif not isinstance(text, str):
            text = str(text)
            
        if not text:
            return 0
            
        # Initialize token count
        tokens = []
        remaining_text = text
        
        # First pass: extract programming tokens
        for token_type, token_set in TokenCounter.PROGRAMMING_TOKENS.items():
            for token in token_set:
                pattern = r'\b' + re.escape(token) + r'\b'
                matches = re.finditer(pattern, remaining_text)
                for match in matches:
                    tokens.append(match.group())
                    remaining_text = remaining_text.replace(match.group(), ' ' * len(match.group()))
        
        # Second pass: handle remaining text using patterns
        for pattern in TokenCounter.TOKEN_PATTERNS:
            matches = re.finditer(pattern, remaining_text)
            for match in matches:
                token = match.group().strip()
                if token:
                    tokens.append(token)
                    remaining_text = remaining_text.replace(match.group(), ' ' * len(match.group()))
        
        # Apply length-based adjustments for very long tokens
        final_count = 0
        for token in tokens:
            # Tokens longer than 8 characters might be split by the tokenizer
            token_length = len(token)
            if token_length > 8:
                # Estimate additional tokens for long strings
                final_count += (token_length + 3) // 4
            else:
                final_count += 1
        
        return final_count
    
    @staticmethod
    def validate_token_count(text: str, claimed_tokens: int, threshold: float = 0.2) -> bool:
        """
        Validate if a claimed token count is within reasonable bounds.
        
        Args:
            text: Input text
            claimed_tokens: Number of tokens claimed
            threshold: Acceptable difference threshold (0.2 = 20%)
            
        Returns:
            bool: True if claimed count is reasonable
        """
        estimated_tokens = TokenCounter.count_tokens(text)
        difference = abs(estimated_tokens - claimed_tokens) / max(estimated_tokens, claimed_tokens)
        return difference <= threshold
    
    @staticmethod
    def get_token_distribution(text: str) -> Dict[str, int]:
        """
        Get distribution of different token types.
        
        Args:
            text: Input text
            
        Returns:
            Dict[str, int]: Count of different token types
        """
        distribution = {
            'words': len(re.findall(r'\b\w+\b', text)),
            'numbers': len(re.findall(r'\b\d+\b', text)),
            'punctuation': len(re.findall(r'[^\w\s]', text)),
            'whitespace': len(re.findall(r'\s+', text)),
            'programming': 0
        }
        
        # Count programming tokens
        for token_type, token_set in TokenCounter.PROGRAMMING_TOKENS.items():
            for token in token_set:
                distribution['programming'] += len(re.findall(r'\b' + re.escape(token) + r'\b', text))
                
        return distribution

def calculate_tokens(text: Union[str, Dict, List]) -> int:
    """
    Calcola accuratamente il numero di token nel testo.
    Questa funzione è mantenuta per compatibilità API ma usa
    la nuova implementazione TokenCounter internamente.
    
    Args:
        text: Testo, dizionario o lista da analizzare
        
    Returns:
        int: Numero di token
    """
    return TokenCounter.count_tokens(text)

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
    
    for filename, file_info in files.items():
        total_size += file_info.get('size', 0)
        language = file_info.get('language', 'text')
        size = format_file_size(file_info.get('size', 0))
        context.append(f"- {filename}: {size} ({language})")
    
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
        'comments': len([l for l in lines if l.strip().startswith('#')]),
        'token_count': calculate_tokens(content),
        'complexity_score': _calculate_complexity_score(content)
    }

def _calculate_complexity_score(content: str) -> float:
    """
    Calcola uno score di complessità basato su vari fattori.
    
    Args:
        content: Contenuto del file
        
    Returns:
        float: Score di complessità (0-10)
    """
    score = 0.0
    
    # Lunghezza del file
    lines = content.split('\n')
    score += min(len(lines) / 100, 3)  # Max 3 punti per lunghezza
    
    # Nidificazione
    max_indent = max((len(l) - len(l.lstrip())) for l in lines) // 4
    score += min(max_indent / 4, 2)  # Max 2 punti per nidificazione
    
    # Funzioni e classi
    functions = len(re.findall(r'def\s+\w+\s*\(', content))
    classes = len(re.findall(r'class\s+\w+[:\(]', content))
    score += min((functions + classes) / 10, 2)  # Max 2 punti per funzioni/classi
    
    # Commenti (meno commenti = più complesso)
    comments = len([l for l in lines if l.strip().startswith('#')])
    comment_ratio = comments / len(lines)
    score += min((1 - comment_ratio) * 2, 2)  # Max 2 punti per mancanza di commenti
    
    # Densità di operatori
    operators = len(re.findall(r'[+\-*/=%&|^~<>]+', content))
    score += min(operators / 100, 1)  # Max 1 punto per densità operatori
    
    return round(score, 2)

@st.cache_data(ttl=3600)
def get_language_metrics(language: str, content: str) -> Dict[str, Any]:
    """
    Ottiene metriche specifiche per il linguaggio.
    
    Args:
        language: Linguaggio di programmazione
        content: Contenuto del file
        
    Returns:
        Dict[str, Any]: Metriche specifiche del linguaggio
    """
    metrics = {
        'language': language,
        'size': len(content),
        'tokens': calculate_tokens(content),
        'complexity': _calculate_complexity_score(content)
    }
    
    # Metriche specifiche per Python
    if language.lower() == 'python':
        metrics.update({
            'imports': len(re.findall(r'^import\s+|^from\s+.*\s+import\s+', content, re.M)),
            'functions': len(re.findall(r'def\s+\w+\s*\(', content)),
            'classes': len(re.findall(r'class\s+\w+[:\(]', content)),
            'decorators': len(re.findall(r'@\w+', content)),
            'docstrings': len(re.findall(r'""".*?"""', content, re.DOTALL))
        })
    
    # Metriche specifiche per JavaScript/TypeScript
    elif language.lower() in ['javascript', 'typescript', 'js', 'ts']:
        metrics.update({
            'imports': len(re.findall(r'^import\s+|require\(', content, re.M)),
            'functions': len(re.findall(r'function\s+\w+\s*\(|=>\s*[{(]', content)),
            'classes': len(re.findall(r'class\s+\w+', content)),
            'interfaces': len(re.findall(r'interface\s+\w+', content)) if language.lower() in ['typescript', 'ts'] else 0,
            'jsx_components': len(re.findall(r'<[A-Z]\w+', content))
        })
    
    return metrics