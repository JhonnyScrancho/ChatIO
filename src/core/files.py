"""
File management for Allegro IO Code Assistant.
Handles file uploads, processing, and caching.
"""

import os
import streamlit as st
from typing import Dict, List, Optional, Tuple
from zipfile import ZipFile
from io import BytesIO
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter
import mimetypes
from src.utils.cache_manager import cache_manager

class FileManager:
    """Gestisce l'upload, il processing e il caching dei file."""
    
    ALLOWED_EXTENSIONS = {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css',
        '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php',
        '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sh',
        '.sql', '.md', '.txt', '.json', '.yml', '.yaml'
    }
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    def __init__(self):
        """Inizializza il FileManager."""
        self.current_path = None
    
    def process_file(self, uploaded_file) -> Optional[Dict]:
        """
        Processa un file caricato.
        
        Args:
            uploaded_file: File caricato tramite st.file_uploader
            
        Returns:
            Optional[Dict]: Informazioni sul file processato
        """
        return self._process_file_cached(uploaded_file)
    
    @staticmethod
    @cache_manager.cache_data(ttl_seconds=300)  # 5 minuti
    def _process_file_cached(uploaded_file) -> Optional[Dict]:
        """Versione cacheable del process_file."""
        if uploaded_file.size > FileManager.MAX_FILE_SIZE:
            st.warning(f"File {uploaded_file.name} troppo grande. Massimo 5MB consentiti.")
            return None
            
        try:
            content = uploaded_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Determina il linguaggio
            try:
                lexer = get_lexer_for_filename(uploaded_file.name)
                language = lexer.name.lower()
            except:
                language = 'text'
            
            # Usiamo una funzione statica per l'highlighting
            highlighted = FileManager._highlight_code_cached(content, language)
            
            return {
                'content': content,
                'language': language,
                'size': len(content),
                'name': uploaded_file.name,
                'highlighted': highlighted
            }
            
        except Exception as e:
            st.warning(f"Errore nel processare {uploaded_file.name}: {str(e)}")
            return None
    
    def process_zip(self, zip_file) -> Dict[str, Dict]:
        """
        Processa un file ZIP.
        
        Args:
            zip_file: File ZIP caricato
            
        Returns:
            Dict[str, Dict]: Mappa dei file processati
        """
        return self._process_zip_cached(zip_file)
    
    @staticmethod
    @cache_manager.cache_data(ttl_seconds=300)  # 5 minuti
    def _process_zip_cached(zip_file) -> Dict[str, Dict]:
        """Versione cacheable del process_zip."""
        processed_files = {}
        total_size = 0
        
        with ZipFile(BytesIO(zip_file.read()), 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.file_size > FileManager.MAX_FILE_SIZE:
                    continue
                    
                # Skip directories and hidden files
                if file_info.filename.endswith('/') or '/.' in file_info.filename:
                    continue
                    
                # Check extension
                ext = os.path.splitext(file_info.filename)[1].lower()
                if ext not in FileManager.ALLOWED_EXTENSIONS:
                    continue
                    
                try:
                    content = zip_ref.read(file_info.filename).decode('utf-8')
                    try:
                        lexer = get_lexer_for_filename(file_info.filename)
                        language = lexer.name.lower()
                    except:
                        language = 'text'
                    
                    highlighted = FileManager._highlight_code_cached(content, language)
                    
                    processed_files[file_info.filename] = {
                        'content': content,
                        'language': language,
                        'size': file_info.file_size,
                        'name': file_info.filename,
                        'highlighted': highlighted
                    }
                    total_size += file_info.file_size
                    
                    if total_size > FileManager.MAX_FILE_SIZE * 3:  # Limite totale ZIP
                        break
                        
                except Exception:
                    continue
                    
        return processed_files
    
    @staticmethod
    @cache_manager.cache_data(ttl_seconds=3600)  # 1 ora
    def _highlight_code_cached(content: str, language: str) -> str:
        """
        Versione cacheable del syntax highlighting.
        
        Args:
            content: Contenuto del file
            language: Linguaggio di programmazione
            
        Returns:
            str: HTML con syntax highlighting
        """
        try:
            lexer = get_lexer_for_filename(f"file.{language}")
        except:
            lexer = TextLexer()
            
        formatter = HtmlFormatter(
            style='monokai',
            linenos=True,
            cssclass='source'
        )
        
        return highlight(content, lexer, formatter)
    
    def get_file_icon(self, filename: str) -> str:
        """
        Restituisce un'icona appropriata per il tipo di file.
        
        Args:
            filename: Nome del file
            
        Returns:
            str: Emoji rappresentativa
        """
        ext = os.path.splitext(filename)[1].lower()
        icons = {
            '.py': '🐍',
            '.js': '📜',
            '.jsx': '⚛️',
            '.ts': '📘',
            '.tsx': '💠',
            '.html': '🌐',
            '.css': '🎨',
            '.java': '☕',
            '.cpp': '⚙️',
            '.c': '🔧',
            '.go': '🔵',
            '.rs': '🦀',
            '.rb': '💎',
            '.php': '🐘',
            '.sql': '🗄️',
            '.md': '📝',
            '.txt': '📄',
            '.json': '📋',
            '.yml': '⚙️',
            '.yaml': '⚙️'
        }
        return icons.get(ext, '📄')
    
    def create_file_tree(self, files: Dict[str, Dict]) -> Dict:
        """
        Crea una struttura ad albero dai file caricati.
        
        Args:
            files: Dizionario dei file processati
            
        Returns:
            Dict: Struttura ad albero dei file
        """
        tree = {}
        for filepath, file_info in files.items():
            current = tree
            parts = filepath.split('/')
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = file_info
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        return tree
    
    @cache_manager.cache_data(ttl_seconds=60)  # 1 minuto
    def analyze_codebase(self, files: Dict[str, Dict]) -> Dict:
        """
        Analizza la codebase per statistiche generali.
        
        Args:
            files: Dizionario dei file processati
            
        Returns:
            Dict: Statistiche sulla codebase
        """
        stats = {
            'total_files': len(files),
            'total_size': 0,
            'languages': {},
            'largest_file': ('', 0),
            'line_count': 0
        }
        
        for file_name, file_info in files.items():
            size = file_info['size']
            lang = file_info['language']
            
            stats['total_size'] += size
            stats['languages'][lang] = stats['languages'].get(lang, 0) + 1
            stats['line_count'] += len(file_info['content'].splitlines())
            
            if size > stats['largest_file'][1]:
                stats['largest_file'] = (file_name, size)
        
        return stats