"""
File management for Allegro IO Code Assistant.
Handles file uploads, processing, and caching.
"""

import os
from core.data_analysis import DataAnalysisManager
import streamlit as st
from typing import Dict, List, Optional, Tuple
from zipfile import ZipFile
from io import BytesIO
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter
import mimetypes
import json
from datetime import datetime

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
        if 'forum_analysis_mode' not in st.session_state:
            st.session_state.forum_analysis_mode = False
        if 'is_forum_json' not in st.session_state:
            st.session_state.is_forum_json = False
        if 'forum_keyword' not in st.session_state:
            st.session_state.forum_keyword = None
            
        # Debug container
        if 'debug_container' not in st.session_state:
            st.session_state.debug_container = st.empty()
    
    def _log_debug(self, message: str):
        """Log debug message to Streamlit."""
        with st.session_state.debug_container.container():
            st.info(f"🔍 Debug: {message}")
    
    def _is_forum_json(self, filename: str, content: str) -> Tuple[bool, Optional[str]]:
        """Verifica se il file JSON è un file di dati di forum."""
        self._log_debug(f"Checking if {filename} is a forum JSON file")
        
        if not filename.endswith('_scraped_data.json'):
            self._log_debug(f"File {filename} does not match the required name pattern")
            return False, None
            
        try:
            data = json.loads(content)
            self._log_debug(f"Successfully parsed JSON from {filename}")
            
            if isinstance(data, list) and len(data) > 0:
                first_item = data[0]
                required_fields = ['url', 'title', 'posts', 'metadata']
                
                # Log structure
                self._log_debug(f"First item fields: {list(first_item.keys())}")
                
                if all(field in first_item for field in required_fields):
                    keyword = filename.replace('_scraped_data.json', '')
                    self._log_debug(f"Found valid forum JSON with keyword: {keyword}")
                    return True, keyword
                else:
                    self._log_debug("Missing required fields in JSON structure")
            else:
                self._log_debug("JSON is not a list or is empty")
        except json.JSONDecodeError as e:
            self._log_debug(f"Failed to parse JSON: {str(e)}")
            
        return False, None
    
    def process_file(self, uploaded_file) -> Optional[Dict]:
        """Processa un file caricato."""
        self._log_debug(f"Processing file: {uploaded_file.name}")
        
        result = self._process_file_cached(uploaded_file)
        
        if result:
            if uploaded_file.name.endswith('.json'):
                self._log_debug("Detected JSON file, checking for forum data")
                
                # Mostra struttura JSON
                try:
                    data = json.loads(result['content'])
                    if isinstance(data, list) and len(data) > 0:
                        self._log_debug(f"JSON structure: {list(data[0].keys())}")
                except:
                    self._log_debug("Failed to analyze JSON structure")
                
                # Verifica se è un JSON di forum
                is_forum, keyword = self._is_forum_json(uploaded_file.name, result['content'])
                if is_forum:
                    self._log_debug(f"✅ Valid forum data detected with keyword: {keyword}")
                    st.session_state.forum_analysis_mode = True
                    st.session_state.is_forum_json = True
                    st.session_state.forum_keyword = keyword
                    result['is_forum_json'] = True
                    result['forum_keyword'] = keyword
                    
                    # Inizializza analisi
                    if 'data_analyzer' not in st.session_state:
                        self._log_debug("Initializing DataAnalysisManager")
                        st.session_state.data_analyzer = DataAnalysisManager()
                    
                    analysis = st.session_state.data_analyzer.initialize_forum_analysis(
                        result['content'], 
                        keyword
                    )
                    if analysis:
                        self._log_debug("Forum analysis initialized successfully")
                        result['analysis'] = analysis
                else:
                    self._log_debug("❌ Not a valid forum JSON file")
        
        return result
    
    @staticmethod
    @st.cache_data
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
                'highlighted': highlighted,
                'upload_time': datetime.now().isoformat()
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
    @st.cache_data
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
                    content = zip_ref.read(file_info.filename).decode('utf-8', errors='ignore')
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
    @st.cache_data
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