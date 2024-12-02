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
        
        Args:
            prompt: Messaggio dell'utente
        """
        if not hasattr(st.session_state, 'processing'):
            st.session_state.processing = False
            
        if not st.session_state.processing and prompt:
            st.session_state.processing = True

            # Verifica se il messaggio è già presente nella chat corrente
            current_messages = self.session.get_messages_from_current_chat()
            is_duplicate = any(
                msg["role"] == "user" and 
                msg["content"] == prompt 
                for msg in current_messages[-2:]  # Controlla solo gli ultimi 2 messaggi
            )
            
            # Aggiungi il messaggio solo se non è un duplicato
            if not is_duplicate:
                self.session.add_message_to_current_chat({
                    "role": "user",
                    "content": prompt
                })
            
            response_container = st.empty()
            artifact_container = st.empty()
            progress_bar = None
            progress_container = None
            
            try:
                with st.spinner("Elaborazione in corso..."):
                    if st.session_state.get('json_analysis_mode', False):
                        # Progress bar per analisi
                        progress_bar = st.progress(0)
                        progress_container = st.empty()
                        
                        # Prepara analisi
                        analyzer = st.session_state.data_analyzer
                        
                        # Aggiorna stato progresso
                        progress_bar.progress(25)
                        progress_container.text("Analisi della query in corso...")
                        
                        # Valida e processa query
                        cleaned_prompt = prompt.strip()
                        if not cleaned_prompt:
                            raise ValueError("Query vuota")
                        
                        # Esegui analisi con gestione cache
                        cache_key = f"{st.session_state.current_chat}:{cleaned_prompt}"
                        if cache_key in st.session_state.analysis_cache:
                            response = st.session_state.analysis_cache[cache_key]
                        else:
                            progress_bar.progress(50)
                            progress_container.text("Elaborazione dati...")
                            response = analyzer.query_data(cleaned_prompt)
                            st.session_state.analysis_cache[cache_key] = response
                        
                        # Aggiorna progresso
                        progress_bar.progress(75)
                        progress_container.text("Formattazione risposta...")
                        
                        # Mostra risposta
                        with response_container:
                            with st.chat_message("assistant"):
                                st.markdown(response)
                        
                        # Registra nella cronologia
                        self.session.add_analysis_result(
                            st.session_state.current_chat,
                            cleaned_prompt,
                            response
                        )
                        
                        # Aggiorna cronologia chat
                        if not is_duplicate:
                            self.session.add_message_to_current_chat({
                                "role": "assistant",
                                "content": response
                            })
                        
                        # Completa
                        progress_bar.progress(100)
                        time.sleep(0.5)  # Breve pausa per mostrare completamento
                        
                    else:
                        # Modalità chat normale
                        response = ""
                        context = self._prepare_chat_context()
                        has_new_content = False
                        
                        for chunk in self.llm.process_request(
                            prompt=prompt,
                            context=context,
                            analysis_type=None
                        ):
                            if chunk:
                                has_new_content = True
                                # Verifica se il chunk è un artifact
                                if isinstance(chunk, dict) and 'type' in chunk and 'content' in chunk:
                                    # È un artifact, renderizzalo nel container dedicato
                                    with artifact_container:
                                        self.code_viewer.render_artifact(chunk)
                                        
                                    # Aggiungi riferimento all'artifact nella risposta
                                    artifact_ref = f"\n[Artifact: {chunk.get('title', 'Code')}]\n"
                                    response += artifact_ref
                                    
                                    # Aggiorna display
                                    with response_container:
                                        with st.chat_message("assistant"):
                                            st.markdown(response)
                                else:
                                    # È testo normale, aggiungilo alla risposta
                                    response += chunk
                                    with response_container:
                                        with st.chat_message("assistant"):
                                            st.markdown(response)
                        
                        # Aggiungi la risposta alla chat solo se c'è nuovo contenuto
                        if has_new_content and not is_duplicate:
                            self.session.add_message_to_current_chat({
                                "role": "assistant",
                                "content": response
                            })
                            
                            # Aggiorna timestamp ultimo messaggio
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
                if progress_bar:
                    progress_bar.empty()
                if progress_container:
                    progress_container.empty()

                # Pulisci container temporanei se non c'è stato contenuto
                if response == "":
                    response_container.empty()
                    artifact_container.empty()

    def _prepare_chat_context(self) -> str:
        """Prepara il contesto per la chat."""
        context = []
        
        # Aggiungi contesto dei file
        if hasattr(st.session_state, 'uploaded_files'):
            for filename, file_info in st.session_state.uploaded_files.items():
                # Gestione speciale per file JSON
                if filename.endswith('.json'):
                    context.append(f"\nJSON File: {filename}\nContent:\n```json\n{file_info['content']}\n```\n")
                else:
                    context.append(f"File: {filename}\n```{file_info['language']}\n{file_info['content']}\n```\n")
        
        # Aggiungi contesto JSON se disponibile, anche se non in modalità analisi
        if st.session_state.get('json_structure'):
            json_structure = st.session_state.get('json_structure', {})
            json_type = st.session_state.get('json_type', 'unknown')
            context.append(f"\nJSON Structure:\nType: {json_type}\nStructure: {json_structure}")
        
        # Aggiungi contesto delle chat precedenti per mantenere coerenza
        current_messages = self.session.get_messages_from_current_chat()
        recent_context = []
        for msg in current_messages[-5:]:  # ultimi 5 messaggi
            if msg["role"] == "user" and msg["content"].strip().startswith('{'):
                try:
                    # Prova a vedere se è JSON valido
                    import json
                    json.loads(msg["content"])
                    recent_context.append(f"\nJSON Input from user:\n```json\n{msg['content']}\n```\n")
                except:
                    pass
        
        if recent_context:
            context.extend(recent_context)
        
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
        # Inizializzazione dello stato - mantenuto dal tuo codice originale
        if 'current_artifact' not in st.session_state:
            st.session_state.current_artifact = None
        if 'artifact_history' not in st.session_state:
            st.session_state.artifact_history = []
        if 'artifact_metadata' not in st.session_state:
            st.session_state.artifact_metadata = {}
        
        # Setup logging - mantenuto dal tuo codice originale
        self.logger = logging.getLogger(__name__)
        
        # Mappatura dei tipi MIME - estesa con i nuovi renderer
        self.mime_types = {
            'application/vnd.ant.code': self._render_code_artifact,
            'text/html': self._render_html_artifact,
            'application/vnd.ant.react': self._render_react_artifact,
            'application/vnd.ant.mermaid': self._render_mermaid_artifact,
            'image/svg+xml': self._render_svg_artifact
        }

    def _get_language_label(self, mime_type: str, specified_lang: Optional[str] = None) -> str:
        """
        Converte il MIME type nel nome del linguaggio per syntax highlighting.
        
        Args:
            mime_type: MIME type dell'artifact
            specified_lang: Linguaggio specificato esplicitamente
            
        Returns:
            str: Nome del linguaggio per syntax highlighting
        """
        try:
            mime_to_lang = {
                'application/vnd.ant.code': lambda lang: lang or 'text',
                'text/html': 'html',
                'application/vnd.ant.react': 'jsx',
                'image/svg+xml': 'xml',
                'application/vnd.ant.mermaid': 'mermaid'
            }
            
            if mime_type in mime_to_lang:
                if callable(mime_to_lang[mime_type]):
                    return mime_to_lang[mime_type](specified_lang)
                return mime_to_lang[mime_type]
            return 'text'
            
        except Exception as e:
            self.logger.error(f"Error determining language: {str(e)}")
            return 'text'

    def _create_copy_button(self, code: str, key: str):
        """Crea un pulsante per copiare il codice."""
        try:
            col1, col2 = st.columns([1, 15])
            with col1:
                if st.button("📋", key=f"copy_{key}", help="Copy to clipboard"):
                    st.session_state[f"copied_{key}"] = True
                    st.session_state.clipboard = code
            with col2:
                if st.session_state.get(f"copied_{key}", False):
                    st.success("Copied to clipboard!")
                    time.sleep(1)
                    st.session_state[f"copied_{key}"] = False
                    
        except Exception as e:
            self.logger.error(f"Error creating copy button: {str(e)}")
            st.error("Unable to create copy button")

    def _render_code_artifact(self, artifact: Dict[str, Any]):
        """Renderizza un artifact di codice."""
        try:
            st.markdown(f"### {artifact.get('title', 'Code')}")
            
            # Determina il linguaggio
            language = self._get_language_label(
                artifact['type'],
                artifact.get('language')
            )
            
            # Container per codice e pulsante copia
            code_container = st.container()
            
            with code_container:
                # Aggiungi pulsante copia
                self._create_copy_button(
                    artifact['content'],
                    artifact.get('identifier', 'code')
                )
                
                # Renderizza il codice
                st.code(artifact['content'], language=language)
                
            # Metadati
            with st.expander("Artifact Metadata"):
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
            st.markdown(f"### {artifact.get('title', 'HTML Preview')}")
            
            # Mostra il codice sorgente
            with st.expander("View Source"):
                st.code(artifact['content'], language='html')
                self._create_copy_button(
                    artifact['content'],
                    artifact.get('identifier', 'html')
                )
            
            # Renderizza HTML
            st.components.v1.html(artifact['content'], height=400)
            
        except Exception as e:
            self.logger.error(f"Error rendering HTML artifact: {str(e)}")
            st.error("Error rendering HTML preview")

    def _render_react_artifact(self, artifact: Dict[str, Any]):
        """Renderizza un artifact React."""
        try:
            st.markdown(f"### {artifact.get('title', 'React Component')}")
            
            # Mostra il codice sorgente
            with st.expander("View Source"):
                st.code(artifact['content'], language='jsx')
                self._create_copy_button(
                    artifact['content'],
                    artifact.get('identifier', 'react')
                )
            
            # Opzione per visualizzare il componente
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
            st.markdown(f"### {artifact.get('title', 'Diagram')}")
            st.mermaid(artifact['content'])
            
            # Aggiungi pulsante copia per il codice Mermaid
            self._create_copy_button(
                artifact['content'],
                artifact.get('identifier', 'mermaid')
            )
            
        except Exception as e:
            self.logger.error(f"Error rendering Mermaid artifact: {str(e)}")
            st.error("Error rendering Mermaid diagram")

    def _render_svg_artifact(self, artifact: Dict[str, Any]):
        """Renderizza un artifact SVG."""
        try:
            st.markdown(f"### {artifact.get('title', 'SVG Image')}")
            st.markdown(artifact['content'], unsafe_allow_html=True)
            
            # Aggiungi pulsante copia per il codice SVG
            self._create_copy_button(
                artifact['content'],
                artifact.get('identifier', 'svg')
            )
            
        except Exception as e:
            self.logger.error(f"Error rendering SVG artifact: {str(e)}")
            st.error("Error rendering SVG image")

    def _update_artifact_history(self, artifact: Dict[str, Any]):
        """Aggiorna la storia degli artifact."""
        try:
            # Aggiorna metadata
            identifier = artifact.get('identifier')
            if identifier:
                if identifier not in st.session_state.artifact_metadata:
                    st.session_state.artifact_metadata[identifier] = {
                        'created_at': datetime.now().isoformat(),
                        'times_viewed': 0
                    }
                st.session_state.artifact_metadata[identifier]['times_viewed'] += 1
            
            # Aggiungi alla storia se è nuovo
            if artifact not in st.session_state.artifact_history:
                st.session_state.artifact_history.append(artifact)
                # Mantieni solo gli ultimi 10 artifact
                if len(st.session_state.artifact_history) > 10:
                    st.session_state.artifact_history.pop(0)
                    
        except Exception as e:
            self.logger.error(f"Error updating artifact history: {str(e)}")

    def render_artifact(self, artifact: Dict[str, Any]):
        """Renderizza un artifact basato sul suo tipo."""
        try:
            if not artifact or 'type' not in artifact:
                return

            # Salva l'artifact corrente
            st.session_state.current_artifact = artifact
            
            # Aggiorna la storia
            self._update_artifact_history(artifact)

            # Trova il renderer appropriato e renderizza
            renderer = self.mime_types.get(artifact['type'])
            if renderer:
                renderer(artifact)
            else:
                st.warning(f"Unsupported artifact type: {artifact['type']}")

        except Exception as e:
            self.logger.error(f"Error rendering artifact: {str(e)}")
            st.error(f"Error rendering artifact: {str(e)}")

    def render(self):
        """Renderizza il componente CodeViewer."""
        try:
            # Mostra l'artifact corrente se presente
            if st.session_state.current_artifact:
                self.render_artifact(st.session_state.current_artifact)
            
            # Mostra la storia degli artifact
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
                            
        except Exception as e:
            self.logger.error(f"Error in main render: {str(e)}")
            st.error("Error rendering code viewer")

    def clear_history(self):
        """Pulisce la storia degli artifact."""
        st.session_state.artifact_history = []
        st.session_state.artifact_metadata = {}
        st.session_state.current_artifact = None

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