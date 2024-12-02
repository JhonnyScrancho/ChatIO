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
from typing import Dict, Any, Optional

class FileExplorer:
    """Component per l'esplorazione e l'upload dei file."""
    
    def __init__(self):
        self.session = SessionManager()
        self.file_manager = FileManager()
        self.json_enabled = False
        self.data_analyzer = DataAnalysisManager()
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = {}
        if 'file_messages_sent' not in st.session_state:
            st.session_state.file_messages_sent = set()
        if 'json_analysis_mode' not in st.session_state:
            st.session_state.json_analysis_mode = False
        if 'initial_analysis_sent' not in st.session_state:
            st.session_state.initial_analysis_sent = False
        # Aggiungiamo queste inizializzazioni
        if 'json_structure' not in st.session_state:
            st.session_state.json_structure = None
        if 'json_type' not in st.session_state:
            st.session_state.json_type = None



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

    def _create_file_tree(self, files: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una struttura ad albero dai file caricati."""
        tree = {}
        for path, content in files.items():
            current = tree
            parts = path.split('/')
            
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            current[parts[-1]] = {'content': content, 'full_path': path}
            
        return tree

    def _render_tree_node(self, path: str, node: Dict[str, Any], prefix: str = ""):
        """Renderizza un nodo dell'albero dei file con stile pipe."""
        items = list(sorted(node.items()))
        for i, (name, content) in enumerate(items):
            is_last = i == len(items) - 1
            
            if isinstance(content, dict) and 'content' not in content:
                st.markdown(f"{prefix}{'└── ' if is_last else '├── '}📁 **{name}/**", unsafe_allow_html=True)
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._render_tree_node(f"{path}/{name}", content, new_prefix)
            else:
                icon = self._get_file_icon(name)
                full_path = content['full_path']
                file_button = f"{prefix}{'└── ' if is_last else '├── '}{icon} {name}"
                
                if st.button(file_button, key=f"file_{full_path}", use_container_width=True):
                    st.session_state.selected_file = full_path
                    st.session_state.current_file = full_path

    def _process_json_file(self, content: str, filename: str) -> bool:
        """Processa un file JSON e determina se è analizzabile."""
        try:
            data = json.loads(content)
            if isinstance(data, list) and len(data) > 0:
                # Check for standard data structure
                if all(field in data[0] for field in ['url', 'title', 'posts']):
                    return True
                # Add other JSON structure checks here
                return True
            return True
        except json.JSONDecodeError:
            return False

    def render(self):
        """Renderizza il componente."""
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
            
            [data-testid="stSidebar"] .element-container:has(button[kind="secondary"]) {
                margin: 0 !important;
                padding: 0 !important;
            }
            
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {
                font-family: monospace !important;
                font-size: 0.9em !important;
                white-space: pre !important;
                line-height: 1.5 !important;
                margin: 0 !important;
            }
            </style>
        """, unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            label=" ",
            type=['py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'md', 'txt', 'json', 'yml', 'yaml', 'zip'],
            accept_multiple_files=True,
            key="file_uploader",
            label_visibility="collapsed"
        )

        if uploaded_files:
            new_files = []
            for file in uploaded_files:
                try:
                    if file.name.endswith('.zip'):
                        import zipfile
                        import io
                        
                        zip_content = zipfile.ZipFile(io.BytesIO(file.read()))
                        for zip_file in zip_content.namelist():
                            if not zip_file.startswith('__') and not zip_file.startswith('.'):
                                try:
                                    if zip_file in st.session_state.uploaded_files:
                                        continue
                                        
                                    content = zip_content.read(zip_file).decode('utf-8', errors='ignore')
                                    st.session_state.uploaded_files[zip_file] = {
                                        'content': content,
                                        'language': zip_file.split('.')[-1],
                                        'name': zip_file
                                    }
                                    new_files.append(zip_file)
                                except Exception:
                                    continue
                    else:
                        if file.name in st.session_state.uploaded_files:
                            continue
                            
                        content = file.read().decode('utf-8')
                        st.session_state.uploaded_files[file.name] = {
                            'content': content,
                            'language': file.name.split('.')[-1],
                            'name': file.name
                        }
                        new_files.append(file.name)

                        if file.name.endswith('.json'):
                            try:
                                # Analizziamo il file JSON
                                analysis = self.file_manager._analyze_json_structure(content, file.name)
                                if analysis.get('is_analyzable', False):
                                    st.session_state.json_structure = analysis.get('structure', {})
                                    st.session_state.json_type = analysis.get('type', 'unknown')
                                    # Reset dello stato di analisi
                                    st.session_state.json_analysis_mode = False
                                    st.session_state.initial_analysis_sent = False
                            except Exception as e:
                                st.error(f"Error analyzing JSON file {file.name}: {str(e)}")

                except Exception as e:
                    st.error(f"Error processing {file.name}: {str(e)}")      

            if new_files and 'chats' in st.session_state and st.session_state.current_chat in st.session_state.chats:
                files_message = "📂 New files uploaded:\n"
                for filename in new_files:
                    files_message += f"- {self._get_file_icon(filename)} {filename}\n"
                
                message_hash = hash(files_message)
                if message_hash not in st.session_state.file_messages_sent:
                    st.session_state.chats[st.session_state.current_chat]['messages'].append({
                        "role": "system",
                        "content": files_message
                    })
                    st.session_state.file_messages_sent.add(message_hash)

        if st.session_state.uploaded_files:
            st.markdown("### 🌲 Files Tree")
            tree = self._create_file_tree(st.session_state.uploaded_files)
            self._render_tree_node("", tree, "")

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

    def process_user_message(self, prompt: str):
        """Processa un nuovo messaggio utente."""
        if not prompt.strip():
            return

        self.session.add_message_to_current_chat({
            "role": "user",
            "content": prompt
        })

        response_container = st.empty()
        
        try:
            with st.spinner("Processing..."):
                if st.session_state.get('json_analysis_mode', False):
                    analyzer = st.session_state.data_analyzer
                    response = analyzer.query_data(prompt)
                    with response_container:
                        with st.chat_message("assistant"):
                            st.markdown(response)
                else:
                    response = ""
                    for chunk in self.llm.process_request(prompt=prompt):
                        if chunk:
                            response += chunk
                            with response_container:
                                with st.chat_message("assistant"):
                                    st.markdown(response)

                if response.strip():
                    self.session.add_message_to_current_chat({
                        "role": "assistant",
                        "content": response
                    })
                    
        except Exception as e:
            st.error(f"Error occurred: {str(e)}")
            with response_container:
                with st.chat_message("assistant"):
                    error_msg = ("❌ Mi dispiace, ho incontrato un errore nell'analisi. "
                              "Puoi riprovare o riformulare la domanda?")
                    st.markdown(error_msg)
                    self.session.add_message_to_current_chat({
                        "role": "assistant",
                        "content": error_msg
                    })

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
        """Renderizza l'interfaccia chat con supporto analisi migliorato."""
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
            for message in self.session.get_messages_from_current_chat():
                # Usa "👲🏿" come role per i messaggi dell'assistente
                role = "👲🏿" if message["role"] == "assistant" else "user"
                with st.chat_message(role):
                    st.markdown(message["content"])

        with artifact_container:
            # Renderizza il CodeViewer
            self.code_viewer.render()            

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
        """
        Gestisce l'input dell'utente con supporto per artifact e streaming.
        Previene duplicazioni e gestisce correttamente lo stato.
        
        Args:
            prompt: Messaggio dell'utente
        """
        if not prompt.strip():
            return

        # Previene elaborazioni multiple dello stesso input
        if hasattr(st.session_state, 'last_processed_prompt'):
            if st.session_state.last_processed_prompt == prompt:
                return
        st.session_state.last_processed_prompt = prompt

        # Controllo dello stato di processing
        if not hasattr(st.session_state, 'processing'):
            st.session_state.processing = False
        
        if st.session_state.processing:
            return

        # Containers per output
        response_container = st.empty()
        artifact_container = st.empty()
        progress_container = None
        progress_bar = None
        status_container = None

        try:
            st.session_state.processing = True
            
            # Aggiungi il messaggio utente solo se non è un duplicato
            current_messages = self.session.get_messages_from_current_chat()
            is_duplicate = any(
                msg["role"] == "user" and 
                msg["content"] == prompt 
                for msg in current_messages[-3:]  # Controlla gli ultimi 3 messaggi
            )
            
            if not is_duplicate:
                self.session.add_message_to_current_chat({
                    "role": "user",
                    "content": prompt
                })

            with st.spinner("Elaborazione in corso..."):
                if st.session_state.get('json_analysis_mode', False):
                    # Progress per analisi JSON
                    progress_bar = st.progress(0)
                    progress_container = st.empty()
                    progress_bar.progress(25)
                    progress_container.text("Analisi della query in corso...")
                    
                    # Gestione analisi JSON
                    analyzer = st.session_state.data_analyzer
                    
                    # Usa cache per prevenire duplicazioni
                    cache_key = f"{st.session_state.current_chat}:{prompt}"
                    
                    progress_bar.progress(50)
                    progress_container.text("Elaborazione dati...")
                    
                    if cache_key in st.session_state.analysis_cache:
                        response = st.session_state.analysis_cache[cache_key]
                    else:
                        response = analyzer.query_data(prompt)
                        st.session_state.analysis_cache[cache_key] = response
                    
                    progress_bar.progress(75)
                    progress_container.text("Formattazione risposta...")
                    
                    # Mostra risposta
                    with response_container:
                        with st.chat_message("assistant"):
                            st.markdown(response)
                    
                    # Aggiorna cronologia solo se non è un duplicato
                    if not is_duplicate:
                        self.session.add_message_to_current_chat({
                            "role": "assistant",
                            "content": response
                        })
                        
                    # Registra analisi
                    self.session.add_analysis_result(
                        st.session_state.current_chat,
                        prompt,
                        response
                    )
                    
                    progress_bar.progress(100)
                    time.sleep(0.5)
                    
                else:
                    # Modalità chat normale
                    response = ""
                    context = self._prepare_chat_context()
                    has_new_content = False
                    word_count = 0
                    tokens_generated = 0
                    status_container = st.empty()
                    
                    for chunk in self.llm.process_request(
                        prompt=prompt,
                        context=context
                    ):
                        if chunk:
                            has_new_content = True
                            
                            # Aggiorna contatori
                            word_count += len(chunk.split())
                            tokens_generated += len(chunk) // 4
                            
                            if tokens_generated % 50 == 0:
                                with status_container:
                                    st.text(f"Generati {word_count} parole, {tokens_generated} tokens...")
                            
                            if isinstance(chunk, dict) and 'type' in chunk and 'content' in chunk:
                                # Gestione artifact
                                with artifact_container:
                                    if not hasattr(st.session_state, 'current_artifact'):
                                        st.session_state.current_artifact = None
                                    st.session_state.current_artifact = chunk
                                    self.code_viewer.render_artifact(chunk)
                                response += f"\n[Artifact: {chunk.get('title', 'Code')}]\n"
                            else:
                                # Testo normale
                                response += chunk
                            
                            # Aggiorna display
                            with response_container:
                                with st.chat_message("assistant"):
                                    st.markdown(response)
                    
                    # Aggiorna chat history solo se c'è nuovo contenuto e non è duplicato
                    if has_new_content and not is_duplicate:
                        self.session.add_message_to_current_chat({
                            "role": "assistant",
                            "content": response
                        })
                        st.session_state.last_message_time = datetime.now().timestamp()

        except Exception as e:
            self.logger.error(f"Error processing user input: {str(e)}", exc_info=True)
            error_msg = f"❌ Si è verificato un errore: {str(e)}"
            with response_container:
                with st.chat_message("assistant"):
                    st.error(error_msg)
                    if not is_duplicate:
                        self.session.add_message_to_current_chat({
                            "role": "assistant",
                            "content": error_msg
                        })
                        
        finally:
            st.session_state.processing = False
            # Pulizia containers
            if progress_bar:
                progress_bar.empty()
            if progress_container:
                progress_container.empty()
            if status_container:
                status_container.empty()
            if not response.strip():
                response_container.empty()
                artifact_container.empty()

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
        """
        Renderizza un artifact basato sul suo tipo.
        Gestisce la visualizzazione e lo stato dell'artifact.
        """
        try:
            if not artifact or 'type' not in artifact:
                return

            # Container per l'artifact
            artifact_container = st.container()
            
            with artifact_container:
                # Header dell'artifact
                col1, col2, col3 = st.columns([6,2,2])
                with col1:
                    st.markdown(f"### {artifact.get('title', 'Code Artifact')}")
                with col2:
                    if st.button("📋 Copy", key=f"copy_{artifact.get('identifier', 'code')}"):
                        st.session_state[f"copied_{artifact.get('identifier', 'code')}"] = True
                with col3:
                    if st.button("❌ Close", key=f"close_{artifact.get('identifier', 'code')}"):
                        st.session_state.current_artifact = None
                        return

                # Rendering basato sul tipo
                renderer = self.mime_types.get(artifact['type'])
                if renderer:
                    renderer(artifact)
                else:
                    st.warning(f"Tipo di artifact non supportato: {artifact['type']}")

                # Aggiungi alla storia se non presente
                if artifact not in st.session_state.artifact_history:
                    if len(st.session_state.artifact_history) >= 10:
                        st.session_state.artifact_history.pop(0)
                    st.session_state.artifact_history.append(artifact)

                # Aggiorna metadata
                identifier = artifact.get('identifier')
                if identifier:
                    if identifier not in st.session_state.artifact_metadata:
                        st.session_state.artifact_metadata[identifier] = {
                            'created_at': datetime.now().isoformat(),
                            'times_viewed': 0
                        }
                    st.session_state.artifact_metadata[identifier]['times_viewed'] += 1
                    st.session_state.artifact_metadata[identifier]['last_viewed'] = datetime.now().isoformat()

        except Exception as e:
            self.logger.error(f"Error rendering artifact: {str(e)}")
            st.error(f"Errore nel rendering dell'artifact: {str(e)}")

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