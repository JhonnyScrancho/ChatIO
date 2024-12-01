"""
File management for Allegro IO Code Assistant.
Handles file uploads, processing, and caching.
"""

import os
from core.data_analysis import DataAnalysisManager
import streamlit as st
from typing import Any, Dict, List, Optional, Tuple
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
    


class FileManager:
    def _analyze_json_structure(self, content: str, filename: str) -> Dict[str, Any]:
        """
        Analizza la struttura del JSON e determina il tipo di dati.
        
        Returns:
            Dict con struttura del JSON e tipo rilevato
        """
        try:
            data = json.loads(content)
            analysis = {
                'is_analyzable': True,
                'type': 'unknown',
                'structure': {},
                'sample_data': None,
                'metadata': {
                    'filename': filename,
                    'analyzed_at': datetime.now().isoformat(),
                    'size': len(content)
                }
            }

            if isinstance(data, list):
                analysis['structure']['is_array'] = True
                analysis['structure']['length'] = len(data)
                
                if data:
                    first_item = data[0]
                    if isinstance(first_item, dict):
                        analysis['structure']['sample_keys'] = list(first_item.keys())
                        analysis['sample_data'] = first_item
                        
                        # Rilevamento automatico del tipo
                        # Time series
                        if any(key in ['timestamp', 'date', 'time'] for key in first_item.keys()):
                            has_numeric = any(isinstance(v, (int, float)) for v in first_item.values())
                            if has_numeric:
                                analysis['type'] = 'time_series'
                        
                        # Entity data
                        elif any(key in ['id', 'uuid', 'name'] for key in first_item.keys()):
                            if 'properties' in first_item or 'attributes' in first_item:
                                analysis['type'] = 'entity'
                        
                        # Nested data
                        elif any(isinstance(v, (list, dict)) for v in first_item.values()):
                            analysis['type'] = 'nested'
                        
                        # Metric data
                        elif any(key in ['value', 'metric', 'measure'] for key in first_item.keys()):
                            analysis['type'] = 'metric'
                            
                        # Forum data (aggiunto per il tuo caso specifico)
                        elif all(key in first_item for key in ['url', 'title', 'posts']):
                            analysis['type'] = 'forum'
            else:
                analysis['structure']['is_array'] = False
                if isinstance(data, dict):
                    analysis['structure']['keys'] = list(data.keys())
                    analysis['sample_data'] = {k: type(v).__name__ for k, v in data.items()}
                    
                    # Configuration data
                    if all(isinstance(v, (str, int, float, bool)) for v in data.values()):
                        analysis['type'] = 'config'

            return analysis

        except json.JSONDecodeError:
            return {'is_analyzable': False, 'error': 'Invalid JSON'}
        except Exception as e:
            return {'is_analyzable': False, 'error': str(e)}

    def process_file(self, uploaded_file) -> Optional[Dict]:
        """Processa un file caricato con supporto migliorato per JSON."""
        if uploaded_file.size > self.MAX_FILE_SIZE:
            st.warning(f"File {uploaded_file.name} troppo grande. Massimo 5MB consentiti.")
            return None
            
        try:
            # Leggi il contenuto del file
            content = uploaded_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Risultato base per tutti i file
            result = {
                'content': content,
                'name': uploaded_file.name,
                'size': len(content),
                'type': 'regular'  # tipo default
            }

            # Gestione specializzata per JSON
            if uploaded_file.name.endswith('.json'):
                try:
                    # Verifica che sia JSON valido
                    json_data = json.loads(content)
                    
                    # Analisi struttura JSON
                    analysis = self._analyze_json_structure(content, uploaded_file.name)
                    if analysis['is_analyzable']:
                        result.update({
                            'type': 'json',
                            'json_analysis': analysis,
                            'json_data': json_data
                        })
                        
                        # Aggiorna lo stato dell'applicazione per JSON
                        st.session_state.json_structure = analysis['structure']
                        st.session_state.json_type = analysis['type']
                        st.session_state.has_json_file = True
                        st.session_state.current_json_file = uploaded_file.name
                        
                except json.JSONDecodeError:
                    st.warning(f"Il file {uploaded_file.name} non è un JSON valido.")
                    return None
                    
            else:
                # Per file non-JSON, aggiungi syntax highlighting
                try:
                    lexer = get_lexer_for_filename(uploaded_file.name)
                    result.update({
                        'language': lexer.name.lower(),
                        'highlighted': self._highlight_code(content, lexer.name.lower())
                    })
                except:
                    result.update({
                        'language': 'text',
                        'highlighted': self._highlight_code(content, 'text')
                    })

            # Aggiorna la lista dei file processati
            if 'uploaded_files' not in st.session_state:
                st.session_state.uploaded_files = {}
            st.session_state.uploaded_files[uploaded_file.name] = result
            
            # Notifica il SessionManager
            if 'session_manager' in st.session_state:
                st.session_state.session_manager.add_file(
                    uploaded_file.name,
                    result
                )
                    
            return result
                    
        except Exception as e:
            st.error(f"Errore nel processare {uploaded_file.name}: {str(e)}")
            return None
    
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