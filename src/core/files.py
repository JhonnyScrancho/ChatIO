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

class FileManager:
    """Gestisce l'upload, il processing e il caching dei file."""
    
    ALLOWED_EXTENSIONS = {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css',
        '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php',
        '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sh',
        '.sql', '.md', '.txt', '.json', '.yml', '.yaml'
    }
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    @st.cache_data
    def process_file(self, uploaded_file) -> Tuple[str, str, int]:
        """
        Processa un file caricato.
        
        Args:
            uploaded_file: File caricato tramite st.file_uploader
            
        Returns:
            Tuple[str, str, int]: (contenuto, linguaggio, dimensione)
        """
        content = uploaded_file.read()
        file_size = len(content)
        
        if file_size > self.MAX_FILE_SIZE:
            raise ValueError(f"File troppo grande. Massimo {self.MAX_FILE_SIZE/1024/1024}MB consentiti")
            
        try:
            content_str = content.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError("File non valido: deve essere un file di testo")
            
        # Determina il linguaggio dal file
        try:
            lexer = get_lexer_for_filename(uploaded_file.name)
            language = lexer.name.lower()
        except:
            language = 'text'
            
        return content_str, language, file_size
    
    @st.cache_data
    def process_zip(self, zip_file) -> Dict[str, Tuple[str, str, int]]:
        """
        Processa un file ZIP.
        
        Args:
            zip_file: File ZIP caricato
            
        Returns:
            Dict[str, Tuple[str, str, int]]: Mappa di (nome_file: (contenuto, linguaggio, dimensione))
        """
        processed_files = {}
        total_size = 0
        
        with ZipFile(BytesIO(zip_file.read()), 'r') as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.file_size > self.MAX_FILE_SIZE:
                    continue
                    
                # Skip directories and hidden files
                if file_info.filename.endswith('/') or '/.' in file_info.filename:
                    continue
                    
                # Check extension
                ext = os.path.splitext(file_info.filename)[1].lower()
                if ext not in self.ALLOWED_EXTENSIONS:
                    continue
                    
                # Process file
                try:
                    content = zip_ref.read(file_info.filename).decode('utf-8')
                    try:
                        lexer = get_lexer_for_filename(file_info.filename)
                        language = lexer.name.lower()
                    except:
                        language = 'text'
                        
                    processed_files[file_info.filename] = (
                        content, language, file_info.file_size
                    )
                    total_size += file_info.file_size
                    
                    if total_size > self.MAX_FILE_SIZE * 3:  # Limite totale ZIP
                        break
                        
                except UnicodeDecodeError:
                    continue
                    
        return processed_files
    
    @st.cache_data
    def highlight_code(self, content: str, language: str) -> str:
        """
        Applica syntax highlighting al codice.
        
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
    
    def create_file_tree(self, files: Dict[str, Tuple[str, str, int]]) -> Dict:
        """
        Crea una struttura ad albero dai file caricati.
        
        Args:
            files: Dizionario dei file processati
            
        Returns:
            Dict: Struttura ad albero dei file
        """
        tree = {}
        for filepath in files.keys():
            current = tree
            parts = filepath.split('/')
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    current[part] = filepath
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        return tree