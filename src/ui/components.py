"""
UI components for Allegro IO Code Assistant.
"""

import streamlit as st
from datetime import datetime
import json
import time
import logging
from src.core.session import SessionManager
from src.core.files import FileManager
from src.core.llm import LLMManager
from src.core.data_analysis import DataAnalysisManager
from typing import Dict, Any, List, Optional

class FileExplorer:
    def __init__(self):
        self.session = SessionManager()
        self.file_manager = FileManager()
        self.data_analyzer = DataAnalysisManager()
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = {}
        if 'file_messages_sent' not in st.session_state:
            st.session_state.file_messages_sent = set()

    def render(self):
        """Renderizza il componente FileExplorer completo."""
        st.markdown("""
            <style>
            [data-testid="stSidebar"] .stButton > button {
                width: auto;
                text-align: left !important;
                padding: 2px 8px !important;
                background: none !important;
                border: none !important;
                font-family: monospace !important;
                font-size: 0.9em !important;
                white-space: pre !important;
                line-height: 1.5 !important;
                color: var(--text-color) !important;
            }
            
            [data-testid="stSidebar"] .stButton > button:hover {
                background-color: var(--primary-color-light) !important;
                color: var(--primary-color) !important;
            }
            
            .file-tree-container {
                margin-top: 1rem;
                border-left: 1px solid rgba(49, 51, 63, 0.2);
                padding-left: 0.5rem;
            }
            
            .file-actions {
                display: flex;
                gap: 0.5rem;
                margin-top: 0.5rem;
            }
            </style>
        """, unsafe_allow_html=True)

        # Upload Section
        uploaded_files = st.file_uploader(
            label="Upload Files",
            type=['py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'md', 'txt', 'json', 'yml', 'yaml', 'zip'],
            accept_multiple_files=True,
            key="file_uploader"
        )

        # Process uploaded files
        if uploaded_files:
            new_files = []
            for file in uploaded_files:
                try:
                    if file.name.endswith('.zip'):
                        zip_files = self.file_manager.process_zip(file)
                        for zip_name, zip_content in zip_files.items():
                            if zip_name not in st.session_state.uploaded_files:
                                st.session_state.uploaded_files[zip_name] = zip_content
                                new_files.append(zip_name)
                    else:
                        if file.name not in st.session_state.uploaded_files:
                            file_info = self.process_uploaded_file(file)
                            if file_info:
                                st.session_state.uploaded_files[file.name] = file_info
                                new_files.append(file.name)
                                
                                # JSON specific handling
                                if file.name.endswith('.json'):
                                    self._handle_json_upload(file.name, file_info)
                except Exception as e:
                    st.error(f"Error processing {file.name}: {str(e)}")

            if new_files:
                self._notify_new_files(new_files)

        # File Tree Section
        if st.session_state.uploaded_files:
            st.markdown("### 🌲 Files")
            
            # File statistics
            total_files = len(st.session_state.uploaded_files)
            total_size = sum(file_info.get('size', 0) for file_info in st.session_state.uploaded_files.values())
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**Total Files:** {total_files}")
            with col2:
                st.markdown(f"**Total Size:** {self._format_size(total_size)}")

            # JSON Analysis Mode Toggle
            has_json = any(f.endswith('.json') for f in st.session_state.uploaded_files)
            if has_json:
                with st.expander("📊 JSON Analysis Settings", expanded=True):
                    json_analysis = st.toggle(
                        'Enable JSON Analysis',
                        value=st.session_state.get('json_analysis_mode', False),
                        key='json_analysis_toggle'
                    )
                    if json_analysis != st.session_state.get('json_analysis_mode', False):
                        self._handle_json_analysis_toggle(json_analysis)
                    
                    if json_analysis:
                        st.markdown(f"**Current JSON Type:** {st.session_state.get('json_type', 'unknown')}")
                        if st.session_state.get('json_structure'):
                            with st.expander("Show JSON Structure"):
                                st.json(st.session_state.json_structure)

            # Render File Tree
            with st.container():
                st.markdown("#### 📂 File Tree")
                tree = self._create_file_tree(st.session_state.uploaded_files)
                self._render_tree_node("", tree)

            # File Actions
            with st.container():
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🗑️ Clear All Files"):
                        self._clear_all_files()
                with col2:
                    if st.button("📥 Download All"):
                        self._download_files()

    
    def process_uploaded_file(self, file) -> Optional[Dict]:
        """Processa un singolo file caricato."""
        try:
            content = file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')

            file_info = {
                'content': content,
                'language': file.name.split('.')[-1],
                'name': file.name,
                'size': len(content),
                'type': 'regular'
            }

            # Gestione speciale per JSON
            if file.name.endswith('.json'):
                try:
                    json_data = json.loads(content)
                    analysis = self.file_manager._analyze_json_structure(content, file.name)
                    if analysis.get('is_analyzable', False):
                        file_info.update({
                            'type': 'json',
                            'json_analysis': analysis,
                            'json_data': json_data
                        })
                        # Aggiorna lo stato JSON globale
                        st.session_state.json_structure = analysis.get('structure', {})
                        st.session_state.json_type = analysis.get('type', 'unknown')
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON in file {file.name}: {str(e)}")
                    return None

            return file_info
        except Exception as e:
            st.error(f"Error processing {file.name}: {str(e)}")
            return None

    def _handle_json_analysis_toggle(self, enabled: bool):
        """Gestisce il toggle dell'analisi JSON."""
        if enabled != st.session_state.get('json_analysis_mode', False):
            st.session_state.json_analysis_mode = enabled
            if enabled:
                # Verifica che ci sia un JSON valido da analizzare
                has_valid_json = any(
                    f_info.get('type') == 'json' and f_info.get('json_analysis')
                    for f_info in st.session_state.uploaded_files.values()
                )
                if not has_valid_json:
                    st.warning("No valid JSON files found for analysis.")
                    st.session_state.json_analysis_mode = False
                    return

                # Reset dello stato di analisi
                st.session_state.initial_analysis_sent = False
                
                # Notifica l'utente
                st.success("JSON analysis mode enabled! You can now ask questions about your JSON data.")
            else:
                # Pulisci la cache di analisi quando si disabilita
                if 'analysis_cache' in st.session_state:
                    st.session_state.analysis_cache = {}
                st.info("JSON analysis mode disabled.")
    
    
    
    def _handle_json_upload(self, filename: str, file_info: dict):
        """Gestisce l'upload di un file JSON."""
        if file_info.get('type') == 'json' and file_info.get('json_analysis'):
            st.session_state.json_structure = file_info['json_analysis'].get('structure')
            st.session_state.json_type = file_info['json_analysis'].get('type')
            
            # Mostra notifica di successo
            st.success(f"JSON file '{filename}' analyzed successfully!")

    def _render_tree_node(self, path: str, node: dict, level: int = 0):
        """Renderizza un nodo dell'albero dei file con stile migliorato."""
        for name, content in sorted(node.items()):
            full_path = f"{path}/{name}" if path else name
            indent = "    " * level
            
            if isinstance(content, dict) and 'content' not in content:
                # Directory
                st.markdown(f"{indent}📁 **{name}/**")
                self._render_tree_node(full_path, content, level + 1)
            else:
                # File
                icon = self._get_file_icon(name)
                col1, col2 = st.columns([6, 1])
                with col1:
                    if st.button(
                        f"{indent}{icon} {name}",
                        key=f"file_{full_path}",
                        help="Click to view/edit file"
                    ):
                        self._select_file(full_path, content)
                with col2:
                    if st.button(
                        "🗑️",
                        key=f"delete_{full_path}",
                        help="Delete file"
                    ):
                        self._delete_file(full_path)

    def _select_file(self, filepath: str, file_info: dict):
        """Gestisce la selezione di un file."""
        st.session_state.selected_file = filepath
        st.session_state.current_file = filepath
        
        # Mostra preview del file
        with st.expander(f"Preview: {filepath}", expanded=True):
            if file_info.get('type') == 'json':
                st.json(file_info.get('json_data', {}))
            else:
                st.code(file_info.get('content', ''), language=file_info.get('language', 'text'))

    def _delete_file(self, filepath: str):
        """Elimina un file."""
        if filepath in st.session_state.uploaded_files:
            del st.session_state.uploaded_files[filepath]
            
            # Reset JSON analysis if needed
            if filepath.endswith('.json'):
                has_other_json = any(
                    f.endswith('.json') 
                    for f in st.session_state.uploaded_files
                )
                if not has_other_json:
                    st.session_state.json_analysis_mode = False
                    st.session_state.json_structure = None
                    st.session_state.json_type = None
            
            st.success(f"File '{filepath}' deleted successfully!")
            st.experimental_rerun()

    def _clear_all_files(self):
        """Pulisce tutti i file."""
        st.session_state.uploaded_files = {}
        st.session_state.json_analysis_mode = False
        st.session_state.json_structure = None
        st.session_state.json_type = None
        st.session_state.file_messages_sent = set()
        st.success("All files cleared successfully!")
        st.experimental_rerun()

    def _download_files(self):
        """Prepara il download di tutti i file."""
        import io
        import zipfile
        
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as zip_file:
            for filename, file_info in st.session_state.uploaded_files.items():
                content = file_info.get('content', '').encode('utf-8')
                zip_file.writestr(filename, content)
        
        st.download_button(
            label="📥 Download Files",
            data=buffer.getvalue(),
            file_name="files.zip",
            mime="application/zip"
        )

    def _format_size(self, size_bytes: int) -> str:
        """Formatta la dimensione in bytes in formato leggibile."""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} GB"

    def _get_file_icon(self, filename: str) -> str:
        """Restituisce l'icona appropriata per il tipo di file."""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        icons = {
            'py': '🐍',
            'js': '📜',
            'jsx': '⚛️',
            'ts': '📘',
            'tsx': '💠',
            'html': '🌐',
            'css': '🎨',
            'md': '📝',
            'txt': '📄',
            'json': '📋',
            'yaml': '⚙️',
            'yml': '⚙️',
            'zip': '📦'
        }
        return icons.get(ext, '📄')

    def _notify_new_files(self, new_files: List[str]):
        """Notifica l'aggiunta di nuovi file."""
        if new_files and hasattr(st.session_state, 'current_chat'):
            files_message = "📂 New files uploaded:\n"
            for filename in new_files:
                icon = self._get_file_icon(filename)
                files_message += f"- {icon} {filename}\n"
            
            message_hash = hash(files_message)
            if message_hash not in st.session_state.file_messages_sent:
                st.session_state.chats[st.session_state.current_chat]['messages'].append({
                    "role": "system",
                    "content": files_message
                })
                st.session_state.file_messages_sent.add(message_hash)

    def _create_file_tree(self, files: Dict[str, Dict]) -> Dict[str, Any]:
        """
        Crea una struttura ad albero dai file caricati.
        
        Args:
            files: Dizionario dei file processati
            
        Returns:
            Dict[str, Any]: Struttura ad albero dei file
        """
        tree = {}
        for filepath, content in files.items():
            current = tree
            parts = filepath.split('/')
            
            # Gestisce ogni parte del path
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Aggiunge il file all'ultimo livello
            current[parts[-1]] = {
                'content': content.get('content', ''),
                'language': content.get('language', 'text'),
                'size': content.get('size', 0),
                'type': content.get('type', 'regular'),
                'full_path': filepath
            }
            
            # Gestione speciale per JSON
            if content.get('type') == 'json':
                current[parts[-1]].update({
                    'json_analysis': content.get('json_analysis', {}),
                    'json_data': content.get('json_data', {})
                })

        # Ordina il tree
        def sort_tree(node):
            if isinstance(node, dict):
                # Se è una directory (non ha 'content')
                if 'content' not in node:
                    return {k: sort_tree(v) for k, v in sorted(node.items())}
                return node
            return node

        return sort_tree(tree)            
    

class ChatInterface:
    """Componente per l'interfaccia chat."""
    
    def __init__(self):
        self.session = SessionManager()
        self.llm = LLMManager()
        self.code_viewer = CodeViewer()
        if 'data_analyzer' not in st.session_state:
            st.session_state.data_analyzer = DataAnalysisManager()
        if 'chats' not in st.session_state:
            st.session_state.chats = {
                'Chat principale': {
                    'messages': [{
                        "role": "assistant",
                        "content": "Ciao! Carica dei file e fammi delle domande su di essi. Posso aiutarti ad analizzarli."
                    }],
                    'created_at': datetime.now().isoformat()
                }
            }
            st.session_state.current_chat = 'Chat principale'
        if 'json_analysis_states' not in st.session_state:
            st.session_state.json_analysis_states = {}
        if 'json_structure' not in st.session_state:
            st.session_state.json_structure = None
        if 'json_type' not in st.session_state:
            st.session_state.json_type = None
        if 'processing' not in st.session_state:
            st.session_state.processing = False
        if 'message_ids' not in st.session_state:     # Aggiungi qui
            st.session_state.message_ids = set()
            
        # Setup logging
        self.logger = logging.getLogger(__name__) 


    def _process_response(self, prompt: str) -> str:
        """Processa la richiesta e genera una risposta."""
        try:
            context = ""
            for filename, file_info in st.session_state.uploaded_files.items():
                context += f"\nFile: {filename}\n```{file_info['language']}\n{file_info['content']}\n```\n"

            response = ""
            placeholder = st.empty()
            with st.spinner("Analyzing..."):
                if st.session_state.get('json_analysis_mode', False) and prompt:
                    analyzer = st.session_state.data_analyzer
                    response = analyzer.query_data(prompt)
                else:
                    for chunk in self.llm.process_request(
                        prompt=prompt,
                        context=context
                    ):
                        response += chunk
                        with placeholder:
                            st.markdown(response)
            return response
        except Exception as e:
            error_msg = f"Error occurred: {str(e)}"
            st.error(error_msg)
            return error_msg


    def _handle_chat_change(self, new_chat: str):
        """Gestisce il cambio di chat preservando lo stato dell'analisi."""
        old_chat = st.session_state.current_chat
        
        # Salva stato analisi della chat corrente
        if old_chat in st.session_state.chats:
            st.session_state.json_analysis_states[old_chat] = {
                'enabled': st.session_state.json_analysis_mode,
                'structure': st.session_state.json_structure,
                'type': st.session_state.json_type,
                'initial_analysis_sent': st.session_state.get('initial_analysis_sent', False)
            }
        
        # Imposta la nuova chat
        st.session_state.current_chat = new_chat
        
        # Ripristina stato analisi per la nuova chat
        if new_chat in st.session_state.json_analysis_states:
            state = st.session_state.json_analysis_states[new_chat]
            st.session_state.json_analysis_mode = state['enabled']
            st.session_state.json_structure = state['structure']
            st.session_state.json_type = state['type']
            st.session_state.initial_analysis_sent = state['initial_analysis_sent']
        else:
            # Reset per nuova chat
            st.session_state.json_analysis_mode = False
            st.session_state.initial_analysis_sent = False

    def _create_new_chat(self):
        """Crea una nuova chat con stato analisi pulito."""
        new_chat_name = f"Chat {len(st.session_state.chats) + 1}"
        st.session_state.chats[new_chat_name] = {
            'messages': [],
            'created_at': datetime.now().isoformat(),
            'analysis_mode': False,
            'analysis_settings': {}
        }
        
        # Reset stati analisi per nuova chat
        st.session_state.json_analysis_mode = False
        st.session_state.initial_analysis_sent = False
        st.session_state.current_chat = new_chat_name
    
    
    def render(self):
        """Renderizza l'interfaccia chat."""
        # Rimuovi il vecchio process_user_message dato che ora usiamo handle_user_input
        
        # Gestione JSON Analysis Toggle
        has_json = any(f.endswith('.json') for f in st.session_state.uploaded_files)
        
        if has_json:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    if st.session_state.get('json_analysis_mode', False):
                        st.markdown("**📊 Modalità Analisi JSON** 🟢")
                    else:
                        st.markdown("**📊 Modalità Analisi JSON** ⚪")
                with col2:
                    json_analysis = st.toggle(
                        'Attiva Analisi',
                        key='chat_json_analysis_mode',
                        help='Abilita analisi dati JSON nella chat'
                    )
                    if json_analysis != st.session_state.get('json_analysis_mode', False):
                        self.handle_analysis_mode_change(json_analysis)
        
        # Render chat messages
        messages_container = st.container()
        artifact_container = st.container()
        
        with messages_container:
            messages = self.session.get_messages_from_current_chat()
            # Previeni duplicati usando ID messaggio
            displayed_ids = set()
            
            for message in messages:
                msg_id = message.get('id', hash(message['content']))
                if msg_id not in displayed_ids:
                    role = "👲🏿" if message["role"] == "assistant" else "user"
                    with st.chat_message(role):
                        st.markdown(message["content"])
                    displayed_ids.add(msg_id)

        # Chat input
        chat_interface = ChatInterface()
        if prompt := st.chat_input("Che minchia vuoi?"):
            if not st.session_state.get('processing', False):
                chat_interface.handle_user_input(prompt)
        
        with artifact_container:
            self.code_viewer.render()

    def _update_session_state(self):
        """Aggiorna e pulisci lo stato della sessione."""
        # Rimuovi messaggi duplicati
        if 'chats' in st.session_state:
            current_chat = st.session_state.chats.get(st.session_state.current_chat, {})
            messages = current_chat.get('messages', [])
            
            # Usa set per tracciare messaggi unici
            unique_messages = []
            seen_contents = set()
            
            for msg in messages:
                msg_content = msg['content']
                if msg_content not in seen_contents:
                    unique_messages.append(msg)
                    seen_contents.add(msg_content)
            
            current_chat['messages'] = unique_messages

    def cleanup_old_states(self):
        """Pulisce stati vecchi o non necessari."""
        # Rimuovi vecchie chiavi di stato non più necessarie
        if 'old_message_processor' in st.session_state:
            del st.session_state.old_message_processor
        
        # Limita la dimensione della cache
        if 'analysis_cache' in st.session_state:
            cache_items = list(st.session_state.analysis_cache.items())
            if len(cache_items) > 100:  # mantieni solo ultimi 100 risultati
                st.session_state.analysis_cache = dict(cache_items[-100:])           

    def handle_analysis_mode_change(self, enabled: bool):
        """Gestisce il cambio di modalità analisi."""
        st.session_state.json_analysis_mode = enabled
        if enabled and not st.session_state.get('initial_analysis_sent', False):
            with st.spinner("Eseguo analisi iniziale..."):
                analyzer = st.session_state.data_analyzer
                initial_analysis = analyzer.get_analysis_summary()
                if initial_analysis:
                    self.session.add_message_to_current_chat({
                        "role": "assistant",
                        "content": initial_analysis
                    })
                    st.session_state.initial_analysis_sent = True
    
    def handle_user_input(self, prompt: str):
        """Gestisce l'input dell'utente con prevenzione duplicati."""
        if not prompt.strip():
            return

        # Genera un ID univoco per il messaggio
        message_id = hashlib.md5(f"{prompt}:{time.time()}".encode()).hexdigest()
        if message_id in st.session_state.message_ids:
            return
        st.session_state.message_ids.add(message_id)

        try:
            st.session_state.processing = True
            response_container = st.empty()
            artifact_container = st.empty()

            # Aggiungi messaggio utente
            self.session.add_message_to_current_chat({
                "role": "user",
                "content": prompt,
                "id": message_id
            })

            if st.session_state.get('json_analysis_mode', False):
                # Determina se usare analisi strutturata o LLM
                if self._is_structured_query(prompt):
                    response = self._handle_structured_analysis(prompt, response_container)
                else:
                    response = self._handle_llm_query(prompt, response_container)
            else:
                response = self._handle_normal_chat(prompt, response_container, artifact_container)

            # Aggiungi risposta alla chat solo se non è vuota e non è un duplicato
            if response.strip():
                response_id = f"response_{message_id}"
                if response_id not in st.session_state.message_ids:
                    self.session.add_message_to_current_chat({
                        "role": "assistant",
                        "content": response,
                        "id": response_id
                    })
                    st.session_state.message_ids.add(response_id)

        except Exception as e:
            st.error(f"Error: {str(e)}")
            self._handle_error(e, response_container)
        finally:
            st.session_state.processing = False
            self._cleanup_old_messages()

    def _is_structured_query(self, query: str) -> bool:
        """Determina se la query richiede analisi strutturata."""
        # Lista espansa di keywords per analisi strutturata
        structured_keywords = {
            'calcola': ['calcola', 'computa', 'determina'],
            'analizza': ['analizza', 'analisi', 'esamina'],
            'trova': ['trova', 'cerca', 'identifica', 'pattern'],
            'statistiche': ['statistiche', 'stats', 'metriche'],
            'conta': ['conta', 'conteggio', 'numera'],
            'somma': ['somma', 'totale', 'aggregato'],
            'media': ['media', 'average', 'mean'],
            'distribuzione': ['distribuzione', 'distribuisci'],
            'raggruppa': ['raggruppa', 'group', 'cluster']
        }
        
        query_lower = query.lower()
        # Controlla tutte le varianti di ogni keyword
        for keyword_group in structured_keywords.values():
            if any(keyword in query_lower for keyword in keyword_group):
                return True
        return False

    def _handle_structured_analysis(self, query: str, response_container: st.container) -> str:
        """Gestisce query di analisi strutturata con feedback visivo."""
        try:
            with response_container:
                with st.status("Analyzing data...", expanded=True) as status:
                    st.write("Preparing analysis...")
                    analyzer = st.session_state.data_analyzer
                    
                    # Fase 1: Preparazione
                    st.write("Processing query...")
                    status.update(label="Processing data", state="running")
                    
                    # Fase 2: Analisi
                    result = analyzer.query_data(query)
                    status.update(label="Analysis complete", state="complete")
                    
                    # Cache del risultato
                    cache_key = f"analysis_{hashlib.md5(query.encode()).hexdigest()}"
                    st.session_state.analysis_cache[cache_key] = result
                    
                    return result
        except Exception as e:
            st.error(f"Analysis error: {str(e)}")
            return f"❌ Error during analysis: {str(e)}"

    def _handle_llm_query(self, query: str, response_container: st.container) -> str:
        """Gestisce query LLM sul JSON con contesto e streaming."""
        try:
            # Prepara il contesto JSON
            context = self._prepare_json_context()
            messages = [
                {"role": "system", "content": "Sei un esperto analista di dati JSON."},
                {"role": "system", "content": context},
                {"role": "user", "content": query}
            ]
            
            # Processa la risposta con streaming
            response = ""
            with response_container:
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    for chunk in self.llm.process_request(messages=messages):
                        response += chunk
                        # Aggiorna il placeholder con il testo accumulato
                        message_placeholder.markdown(response + "▌")
                    # Aggiorna una ultima volta senza il cursore
                    message_placeholder.markdown(response)
            
            return response
            
        except Exception as e:
            st.error(f"LLM query error: {str(e)}")
            return f"❌ Error processing query: {str(e)}"

    def _handle_normal_chat(self, prompt: str, response_container: st.container, 
                        artifact_container: st.container) -> str:
        """Gestisce chat normale con supporto artifact e streaming."""
        try:
            response = ""
            has_artifact = False
            
            with response_container:
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    
                    for chunk in self.llm.process_request(prompt=prompt):
                        if isinstance(chunk, dict) and chunk.get('type') == 'artifact':
                            # Gestione artifact
                            with artifact_container:
                                self.code_viewer.render_artifact(chunk)
                            response += f"\n[Artifact: {chunk.get('title', 'Code')}]\n"
                            has_artifact = True
                        else:
                            response += chunk
                            # Aggiorna il placeholder con il testo accumulato
                            message_placeholder.markdown(response + "▌")
                    
                    # Aggiorna una ultima volta senza il cursore
                    message_placeholder.markdown(response)
            
            # Se c'è stato un artifact, aggiungi un separatore
            if has_artifact:
                response += "\n---\n"
            
            return response
            
        except Exception as e:
            st.error(f"Chat error: {str(e)}")
            return f"❌ Error in conversation: {str(e)}"

    def _prepare_json_context(self) -> str:
        """Prepara il contesto completo per l'analisi JSON."""
        json_type = st.session_state.get('json_type', 'unknown')
        structure = st.session_state.get('json_structure', {})
        
        context = [
            f"Analyzing JSON data of type: {json_type}",
            "\nStructure:",
            f"- Type: {'Array of objects' if structure.get('is_array') else 'Single object'}",
            f"- Fields: {', '.join(structure.get('sample_keys', structure.get('keys', [])))}",
            f"\nSample data available: {bool(structure.get('sample_data'))}",
            "\nYou can provide detailed analysis and insights about this data."
        ]
        
        # Aggiungi informazioni specifiche per tipo
        if json_type == 'time_series':
            context.extend([
                "\nTime series specific context:",
                "- Data includes temporal information",
                "- Can analyze trends and patterns over time",
                "- Can identify seasonality and anomalies"
            ])
        elif json_type == 'entity':
            context.extend([
                "\nEntity data specific context:",
                "- Contains entity properties and attributes",
                "- Can analyze relationships and patterns",
                "- Can provide property distributions"
            ])
        
        return "\n".join(context)

    def _handle_error(self, error: Exception, container: st.container):
        """Gestisce gli errori in modo user-friendly."""
        with container:
            error_message = f"❌ {str(error)}"
            st.error(error_message)
            
            # Aggiungi il messaggio di errore alla chat
            self.session.add_message_to_current_chat({
                "role": "assistant",
                "content": error_message
            })

    def _cleanup_old_messages(self):
        """Pulisce i vecchi ID dei messaggi per gestire la memoria."""
        # Mantieni solo gli ultimi 1000 ID
        if len(st.session_state.message_ids) > 1000:
            st.session_state.message_ids = set(list(st.session_state.message_ids)[-1000:])

    def _prepare_chat_context(self) -> str:
        """Prepara il contesto per la chat includendo informazioni su file e JSON."""
        context = []
        
        # Aggiungi contesto dei file
        if hasattr(st.session_state, 'uploaded_files'):
            for filename, file_info in st.session_state.uploaded_files.items():
                if file_info['type'] == 'json':
                    # Gestione speciale per JSON
                    context.append(f"\nJSON File: {filename}")
                    if 'json_analysis' in file_info:
                        context.append(f"Type: {file_info['json_analysis']['type']}")
                        context.append(f"Structure: {file_info['json_analysis']['structure']}")
                else:
                    # Altri file
                    context.append(f"\nFile: {filename}")
                    context.append(f"Type: {file_info.get('language', 'text')}")
                    context.append(f"Content:\n```{file_info.get('language', '')}\n{file_info['content']}\n```\n")
        
        # Aggiungi contesto JSON se in modalità analisi
        if st.session_state.get('json_analysis_mode', False):
            json_structure = st.session_state.get('json_structure', {})
            json_type = st.session_state.get('json_type', 'unknown')
            context.append(f"\nActive JSON Analysis Mode:")
            context.append(f"Type: {json_type}")
            context.append(f"Structure: {json_structure}")
        
        # Aggiungi contesto delle chat recenti
        current_messages = self.session.get_messages_from_current_chat()
        recent_context = []
        for msg in current_messages[-5:]:  # ultimi 5 messaggi
            if msg["role"] == "user" and msg["content"].strip():
                recent_context.append(f"Previous user query: {msg['content']}")
            elif msg["role"] == "assistant" and msg["content"].strip():
                recent_context.append(f"Previous response: {msg['content'][:100]}...")
        
        if recent_context:
            context.extend(["\nRecent Conversation Context:", *recent_context])
        
        return "\n".join(context)

    def render_analysis_status(self):
        """Renderizza informazioni sullo stato dell'analisi."""
        if st.session_state.get('json_analysis_mode', False):
            with st.container():
                json_type = st.session_state.get('json_type', 'unknown')
                st.markdown(f"""
                **Current Analysis Status:**
                - Type: {json_type}
                - Mode: Active 🟢
                - Cache: {len(st.session_state.analysis_cache)} entries
                """)
                
                # Mostra suggerimenti basati sul tipo
                if json_type == 'time_series':
                    st.markdown("""
                    **Suggested queries:**
                    - "Show me the overall trend"
                    - "Find seasonal patterns"
                    - "Identify outliers"
                    """)
                elif json_type == 'entity':
                    st.markdown("""
                    **Suggested queries:**
                    - "Analyze property distributions"
                    - "Find common patterns"
                    - "Show relationships"
                    """)
                elif json_type == 'metric':
                    st.markdown("""
                    **Suggested queries:**
                    - "Compare metrics"
                    - "Show correlations"
                    - "Find anomalies"
                    """)
    
    def render_chat_controls(self):
        """Renderizza i controlli della chat."""
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            current_chat = st.selectbox(
                " ",
                options=list(st.session_state.chats.keys()),
                index=list(st.session_state.chats.keys()).index(st.session_state.current_chat),
                label_visibility="collapsed"
            )
            if current_chat != st.session_state.current_chat:
                st.session_state.current_chat = current_chat
        
        with col2:
            if st.button("🆕", help="New chat"):
                new_chat_name = f"Chat {len(st.session_state.chats) + 1}"
                st.session_state.chats[new_chat_name] = {
                    'messages': [],
                    'created_at': datetime.now().isoformat()
                }
                st.session_state.current_chat = new_chat_name
        
        with col3:
            if st.button("✏️", help="Rename chat"):
                st.session_state.renaming = True
        
        with col4:
            if len(st.session_state.chats) > 1 and st.button("🗑️", help="Delete chat"):
                del st.session_state.chats[st.session_state.current_chat]
                st.session_state.current_chat = list(st.session_state.chats.keys())[0]

class CodeViewer:
    """Componente per la visualizzazione degli artifact di codice."""
    
    def __init__(self):
        """Inizializza il CodeViewer."""
        if 'current_artifact' not in st.session_state:
            st.session_state.current_artifact = None
        if 'artifact_history' not in st.session_state:
            st.session_state.artifact_history = []
        if 'artifact_metadata' not in st.session_state:
            st.session_state.artifact_metadata = {}
            
        self.logger = logging.getLogger(__name__)
        
        # Mappatura dei tipi MIME per i renderer
        self.mime_types = {
            'application/vnd.ant.code': self._render_code_artifact,
            'text/html': self._render_html_artifact,
            'application/vnd.ant.react': self._render_react_artifact,
            'application/vnd.ant.mermaid': self._render_mermaid_artifact,
            'image/svg+xml': self._render_svg_artifact
        }

    def render_artifact(self, artifact: Dict[str, Any]):
        """Renderizza un artifact con gestione stato migliorata."""
        try:
            if not artifact or 'type' not in artifact:
                return

            # Genera ID univoco per l'artifact
            artifact_id = artifact.get('identifier', f"artifact_{time.time()}")
            
            # Container per l'artifact
            with st.container():
                col1, col2 = st.columns([6,1])
                with col1:
                    st.markdown(f"### {artifact.get('title', 'Code Artifact')}")
                with col2:
                    if st.button("❌", key=f"close_{artifact_id}"):
                        return

                # Rendering basato sul tipo
                if artifact['type'] == 'application/vnd.ant.code':
                    with st.expander("Show Code", expanded=True):
                        st.code(artifact['content'], language=artifact.get('language', 'python'))
                elif artifact['type'] == 'text/html':
                    st.components.v1.html(artifact['content'], height=400)
                elif artifact['type'] == 'image/svg+xml':
                    st.markdown(artifact['content'], unsafe_allow_html=True)
                elif artifact['type'] == 'application/vnd.ant.mermaid':
                    st.mermaid(artifact['content'])

                # Salva l'artifact nella storia
                self._save_to_history(artifact)

        except Exception as e:
            st.error(f"Error rendering artifact: {str(e)}")

    def _save_to_history(self, artifact: Dict[str, Any]):
        """Salva l'artifact nella storia con gestione duplicati."""
        if 'artifact_history' not in st.session_state:
            st.session_state.artifact_history = []

        # Previeni duplicati
        artifact_id = artifact.get('identifier')
        if not any(a.get('identifier') == artifact_id for a in st.session_state.artifact_history):
            if len(st.session_state.artifact_history) >= 10:
                st.session_state.artifact_history.pop(0)
            st.session_state.artifact_history.append(artifact)        

    def _render_code_artifact(self, artifact: Dict[str, Any]):
        """Renderizza un artifact di codice."""
        try:
            # Determina il linguaggio
            language = artifact.get('language', 'text')
            
            # Container per il codice
            with st.expander("Show Code", expanded=True):
                st.code(artifact['content'], language=language)
                
            # Metadata
            with st.expander("Metadata"):
                st.json({
                    'type': artifact['type'],
                    'language': language,
                    'created_at': st.session_state.artifact_metadata.get(
                        artifact.get('identifier', ''),
                        {'created_at': datetime.now().isoformat()}
                    )['created_at']
                })
                
        except Exception as e:
            self.logger.error(f"Error rendering code artifact: {str(e)}")
            st.error("Error rendering code artifact")

    def _render_html_artifact(self, artifact: Dict[str, Any]):
        """Renderizza un artifact HTML."""
        try:
            # Mostra il codice sorgente
            with st.expander("View Source", expanded=False):
                st.code(artifact['content'], language='html')
            
            # Renderizza HTML
            st.components.v1.html(artifact['content'], height=400)
            
        except Exception as e:
            self.logger.error(f"Error rendering HTML artifact: {str(e)}")
            st.error("Error rendering HTML preview")

    def _render_react_artifact(self, artifact: Dict[str, Any]):
        """Renderizza un artifact React."""
        try:
            # Mostra il codice sorgente
            with st.expander("View Source", expanded=False):
                st.code(artifact['content'], language='jsx')
            
            # Preview del componente
            if st.toggle("Show Preview", key=f"preview_{artifact.get('identifier', 'react')}"):
                st.write("Component Preview:")
                st.components.v1.html(
                    f"""
                    <div id="react-root"></div>
                    <script type="text/babel">
                        {artifact['content']}
                    </script>
                    """,
                    height=400
                )
                
        except Exception as e:
            self.logger.error(f"Error rendering React artifact: {str(e)}")
            st.error("Error rendering React component")

    def _render_mermaid_artifact(self, artifact: Dict[str, Any]):
        """Renderizza un artifact Mermaid."""
        try:
            st.mermaid(artifact['content'])
            
        except Exception as e:
            self.logger.error(f"Error rendering Mermaid artifact: {str(e)}")
            st.error("Error rendering Mermaid diagram")

    def _render_svg_artifact(self, artifact: Dict[str, Any]):
        """Renderizza un artifact SVG."""
        try:
            st.markdown(artifact['content'], unsafe_allow_html=True)
            
        except Exception as e:
            self.logger.error(f"Error rendering SVG artifact: {str(e)}")
            st.error("Error rendering SVG image")

    def render_history(self):
        """Renderizza la storia degli artifact."""
        if st.session_state.artifact_history:
            with st.expander("Previous Artifacts"):
                for idx, artifact in enumerate(reversed(st.session_state.artifact_history[-5:])):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        if st.button(
                            f"📄 {artifact.get('title', f'Artifact {len(st.session_state.artifact_history) - idx}')}",
                            key=f"history_{idx}"
                        ):
                            st.session_state.current_artifact = artifact
                            st.experimental_rerun()
                    with col2:
                        meta = st.session_state.artifact_metadata.get(
                            artifact.get('identifier', ''),
                            {}
                        )
                        st.text(f"Views: {meta.get('times_viewed', 0)}")

    def render(self):
        """Renderizza il componente CodeViewer."""
        try:
            # Mostra l'artifact corrente se presente
            if st.session_state.current_artifact:
                self.render_artifact(st.session_state.current_artifact)
            
            # Mostra la storia degli artifact
            self.render_history()
            
        except Exception as e:
            self.logger.error(f"Error in main render: {str(e)}")
            st.error("Error rendering code viewer")

    def clear_history(self):
        """Pulisce la storia degli artifact."""
        st.session_state.artifact_history = []
        st.session_state.artifact_metadata = {}
        st.session_state.current_artifact = None

    def _generate_artifact_key(self, artifact: Dict[str, Any]) -> str:
        """
        Genera una chiave univoca per l'artifact.
        
        Args:
            artifact: L'artifact per cui generare la chiave
            
        Returns:
            str: Chiave univoca
        """
        components = [
            artifact.get('type', 'unknown'),
            artifact.get('identifier', ''),
            artifact.get('title', ''),
            str(len(artifact.get('content', '')))
        ]
        return hashlib.md5('|'.join(components).encode()).hexdigest()

    def save_artifact(self, artifact: Dict[str, Any]):
        """
        Salva un artifact nella session state e aggiorna i metadata.
        
        Args:
            artifact: Artifact da salvare
        """
        if not artifact or 'type' not in artifact:
            return False

        try:
            # Genera chiave
            key = self._generate_artifact_key(artifact)
            
            # Aggiorna session state
            if 'saved_artifacts' not in st.session_state:
                st.session_state.saved_artifacts = {}
            
            st.session_state.saved_artifacts[key] = {
                'artifact': artifact,
                'saved_at': datetime.now().isoformat(),
                'times_accessed': 0
            }
            
            # Aggiorna metadata
            identifier = artifact.get('identifier')
            if identifier:
                st.session_state.artifact_metadata[identifier] = {
                    'key': key,
                    'created_at': datetime.now().isoformat(),
                    'times_viewed': 0,
                    'type': artifact['type']
                }
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving artifact: {str(e)}")
            return False

    def load_artifact(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Carica un artifact salvato.
        
        Args:
            key: Chiave dell'artifact
            
        Returns:
            Optional[Dict[str, Any]]: Artifact se trovato, None altrimenti
        """
        try:
            if 'saved_artifacts' not in st.session_state:
                return None
                
            saved = st.session_state.saved_artifacts.get(key)
            if not saved:
                return None
                
            # Aggiorna contatori
            saved['times_accessed'] += 1
            
            # Aggiorna metadata
            artifact = saved['artifact']
            identifier = artifact.get('identifier')
            if identifier and identifier in st.session_state.artifact_metadata:
                st.session_state.artifact_metadata[identifier]['times_viewed'] += 1
                st.session_state.artifact_metadata[identifier]['last_accessed'] = datetime.now().isoformat()
                
            return artifact
            
        except Exception as e:
            self.logger.error(f"Error loading artifact: {str(e)}")
            return None

    def _update_artifact_view(self, artifact: Dict[str, Any]):
        """
        Aggiorna le statistiche di visualizzazione di un artifact.
        
        Args:
            artifact: Artifact visualizzato
        """
        try:
            identifier = artifact.get('identifier')
            if not identifier:
                return
                
            if identifier not in st.session_state.artifact_metadata:
                st.session_state.artifact_metadata[identifier] = {
                    'created_at': datetime.now().isoformat(),
                    'times_viewed': 0,
                    'last_viewed': None,
                    'type': artifact['type']
                }
                
            metadata = st.session_state.artifact_metadata[identifier]
            metadata['times_viewed'] += 1
            metadata['last_viewed'] = datetime.now().isoformat()
            
            # Aggiorna anche nella storia
            if artifact in st.session_state.artifact_history:
                idx = st.session_state.artifact_history.index(artifact)
                st.session_state.artifact_history[idx] = artifact
                
        except Exception as e:
            self.logger.error(f"Error updating artifact view: {str(e)}")

    def cleanup_old_artifacts(self, max_age_days: int = 7):
        """
        Pulisce gli artifact vecchi.
        
        Args:
            max_age_days: Età massima in giorni degli artifact da mantenere
        """
        try:
            if 'saved_artifacts' not in st.session_state:
                return
                
            current_time = datetime.now()
            keys_to_remove = []
            
            for key, saved in st.session_state.saved_artifacts.items():
                saved_time = datetime.fromisoformat(saved['saved_at'])
                if (current_time - saved_time).days > max_age_days:
                    keys_to_remove.append(key)
                    
            for key in keys_to_remove:
                del st.session_state.saved_artifacts[key]
                
            # Pulisci anche metadata orfani
            if st.session_state.artifact_metadata:
                metadata_to_remove = []
                for identifier, metadata in st.session_state.artifact_metadata.items():
                    if 'key' in metadata and metadata['key'] not in st.session_state.saved_artifacts:
                        metadata_to_remove.append(identifier)
                        
                for identifier in metadata_to_remove:
                    del st.session_state.artifact_metadata[identifier]
                    
        except Exception as e:
            self.logger.error(f"Error cleaning up artifacts: {str(e)}")

    def get_artifact_stats(self) -> Dict[str, Any]:
        """
        Restituisce statistiche sugli artifact.
        
        Returns:
            Dict[str, Any]: Statistiche degli artifact
        """
        stats = {
            'total_artifacts': len(st.session_state.get('saved_artifacts', {})),
            'total_views': sum(
                meta.get('times_viewed', 0) 
                for meta in st.session_state.artifact_metadata.values()
            ),
            'types_distribution': {},
            'most_viewed': None,
            'last_viewed': None
        }
        
        # Calcola distribuzione tipi
        for meta in st.session_state.artifact_metadata.values():
            artifact_type = meta.get('type', 'unknown')
            stats['types_distribution'][artifact_type] = stats['types_distribution'].get(artifact_type, 0) + 1
        
        # Trova più visto
        if st.session_state.artifact_metadata:
            most_viewed_id = max(
                st.session_state.artifact_metadata.items(),
                key=lambda x: x[1].get('times_viewed', 0)
            )[0]
            stats['most_viewed'] = {
                'identifier': most_viewed_id,
                'views': st.session_state.artifact_metadata[most_viewed_id]['times_viewed']
            }
        
        # Trova ultimo visto
        last_viewed = None
        for meta in st.session_state.artifact_metadata.values():
            if meta.get('last_viewed'):
                if not last_viewed or meta['last_viewed'] > last_viewed:
                    last_viewed = meta['last_viewed']
        stats['last_viewed'] = last_viewed
        
        return stats    

class ModelSelector:
    """Componente per la selezione del modello LLM."""
    
    def __init__(self):
        self.session = SessionManager()
    
    def render(self):
        """Renderizza il componente."""
        models = {
            'gpt-4': '🧠 GPT-4 (Expert)',
            'gpt-4o-mini': '⚡ GPT-4 Mini (Fast)',
            'o1-mini': '🚀 O1 Mini (Fast)',
            'o1-preview': '🔍 O1 Preview (Advanced)',
            'claude-3-5-sonnet-20241022': '🎭 Claude 3.5 Sonnet (Detailed)'
        }
        
        current_model = self.session.get_current_model()
        selected = st.selectbox(
            " ",
            list(models.keys()),
            format_func=lambda x: models[x],
            index=list(models.keys()).index(current_model),
            label_visibility="collapsed"
        )
        
        if selected != current_model:
            self.session.set_current_model(selected)

class StatsDisplay:
    """Componente per la visualizzazione delle statistiche."""
    
    def __init__(self):
        self.session = SessionManager()
    
    def render(self):
        """Renderizza il componente."""
        stats = self.session.get_stats()
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Tokens Used",
                f"{stats['token_count']:,}",
                delta=None
            )
        
        with col2:
            st.metric(
                "Cost ($)",
                f"${stats['cost']:.3f}",
                delta=None
            )