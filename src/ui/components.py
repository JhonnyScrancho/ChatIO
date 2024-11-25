"""
UI components for Allegro IO Code Assistant.
"""

import streamlit as st
from datetime import datetime
from src.core.session import SessionManager
from src.core.files import FileManager
from src.core.llm import LLMManager
from typing import Dict, Any

class FileExplorer:
    """Component per l'esplorazione e l'upload dei file."""
    
    def __init__(self):
        self.session = SessionManager()
        self.file_manager = FileManager()
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = {}
        if 'file_messages_sent' not in st.session_state:
            st.session_state.file_messages_sent = set()

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
        """
        Crea una struttura ad albero dai file caricati.
        
        Args:
            files: Dict con i file caricati
            
        Returns:
            Dict con la struttura ad albero
        """
        tree = {}
        for path, content in files.items():
            current = tree
            parts = path.split('/')
            
            # Processa tutte le parti tranne l'ultima (file)
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Aggiungi il file con il path completo
            current[parts[-1]] = {'content': content, 'full_path': path}
            
        return tree

    def _render_tree_node(self, path: str, node: Dict[str, Any], prefix: str = ""):
        """Renderizza un nodo dell'albero dei file con pipe style."""
        items = list(sorted(node.items()))
        for i, (name, content) in enumerate(items):
            is_last = i == len(items) - 1
            
            if isinstance(content, dict) and 'content' not in content:
                # Directory
                st.markdown(f"{prefix}{'└── ' if is_last else '├── '}📁 **{name}/**", unsafe_allow_html=True)
                new_prefix = prefix + ("    " if is_last else "│   ")
                self._render_tree_node(f"{path}/{name}", content, new_prefix)
            else:
                # File
                icon = self._get_file_icon(name)
                full_path = content['full_path']
                file_button = f"{prefix}{'└── ' if is_last else '├── '}{icon} {name}"
                
                if st.button(file_button, key=f"file_{full_path}", use_container_width=True):
                    st.session_state.selected_file = full_path
                    st.session_state.current_file = full_path

    def render(self):
        """Renderizza il componente."""
        st.markdown("""
            <style>
                /* File Explorer specifico */
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
            
            /* Solo per i markdown delle directory nel file explorer */
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
                    # Gestione file ZIP
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
                except Exception as e:
                    st.error(f"Error processing {file.name}: {str(e)}")

            if new_files and 'chats' in st.session_state and st.session_state.current_chat in st.session_state.chats:
                files_message = "📂 Nuovi file caricati:\n"
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
            st.markdown("### 📁 Files")
            tree = self._create_file_tree(st.session_state.uploaded_files)
            self._render_tree_node("", tree, "")

class ChatInterface:
    """Componente per l'interfaccia chat."""
    
    def __init__(self):
        self.session = SessionManager()
        self.llm = LLMManager()
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

    def _process_response(self, prompt: str) -> str:
        """Processa la richiesta e genera una risposta."""
        try:
            # Prepara il contesto completo per l'LLM
            context = ""
            for filename, file_info in st.session_state.uploaded_files.items():
                context += f"\nFile: {filename}\n```{file_info['language']}\n{file_info['content']}\n```\n"

            response = ""
            placeholder = st.empty()
            with st.spinner("Analyzing code..."):
                for chunk in self.llm.process_request(
                    prompt=prompt,
                    context=context
                ):
                    response += chunk
                    # Aggiorna il placeholder con la risposta parziale
                    with placeholder:
                        st.markdown(response)
            return response
        except Exception as e:
            error_msg = f"Mi dispiace, si è verificato un errore: {str(e)}"
            st.error(error_msg)
            return error_msg
        
    def render_chat_controls(self):
        """Renderizza i controlli per la gestione delle chat."""
        st.markdown("""
            <style>
                .chat-controls {
                    display: flex;
                    gap: 1rem;
                    margin-bottom: 1rem;
                }
                .stSelectbox {
                    flex-grow: 1;
                }
            </style>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            # Selettore chat corrente
            current_chat = st.selectbox(
            label=" ",
            options=list(st.session_state.chats.keys()),
            index=list(st.session_state.chats.keys()).index(st.session_state.current_chat),
            label_visibility="collapsed"
        )
        if current_chat != st.session_state.current_chat:
            st.session_state.current_chat = current_chat

        with col2:
            # Pulsante nuova chat
            if st.button("🆕", use_container_width=True):
                new_chat_name = f"Chat {len(st.session_state.chats) + 1}"
                st.session_state.chats[new_chat_name] = {
                    'messages': [],
                    'created_at': datetime.now().isoformat()
                }
                st.session_state.current_chat = new_chat_name

        with col3:
            # Pulsante rinomina
            if st.button("✏️", use_container_width=True):
                st.session_state.renaming = True

        with col4:
            # Pulsante elimina
            if len(st.session_state.chats) > 1 and st.button("🗑️", use_container_width=True):
                if st.session_state.current_chat in st.session_state.chats:
                    del st.session_state.chats[st.session_state.current_chat]
                    st.session_state.current_chat = list(st.session_state.chats.keys())[0]

        # Dialog per rinominare la chat
        if getattr(st.session_state, 'renaming', False):
            with st.form("rename_chat"):
                new_name = st.text_input("Nuovo nome", value=st.session_state.current_chat)
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Salva"):
                        if new_name and new_name != st.session_state.current_chat:
                            # Rinomina la chat
                            st.session_state.chats[new_name] = st.session_state.chats.pop(st.session_state.current_chat)
                            st.session_state.current_chat = new_name
                        st.session_state.renaming = False
                with col2:
                    if st.form_submit_button("Annulla"):
                        st.session_state.renaming = False

    def process_user_message(self, prompt: str):
        """
        Processa un nuovo messaggio utente con debug dettagliato.
        """
        if not prompt.strip():
            return
            
        # Container per debug
        debug_container = st.empty()
        
        def show_debug(title: str, content: Any):
            """Helper per mostrare informazioni di debug."""
            with debug_container:
                st.write(f"🔍 DEBUG - {title}:")
                st.code(str(content))
        
        chat_container = st.container()
        
        with chat_container:
            show_debug("Prompt ricevuto", prompt)
            
            # Aggiungi il messaggio utente
            st.session_state.chats[st.session_state.current_chat]['messages'].append({
                "role": "user",
                "content": prompt
            })
            
            show_debug("Stato messaggi pre-elaborazione", 
                      st.session_state.chats[st.session_state.current_chat]['messages'])

            # Processa la risposta con debug
            response = ""
            with st.spinner("Elaborazione in corso..."):
                try:
                    show_debug("Inizia elaborazione LLM", "Chiamata a process_request")
                    
                    chunks_received = 0
                    total_length = 0
                    
                    for chunk in self.llm.process_request(prompt=prompt):
                        chunks_received += 1
                        if chunk:
                            total_length += len(chunk)
                            response += chunk
                            
                        # Aggiorna debug ogni 5 chunks
                        if chunks_received % 5 == 0:
                            show_debug("Stato streaming", {
                                "chunks_ricevuti": chunks_received,
                                "lunghezza_totale": total_length,
                                "ultimo_chunk": chunk,
                                "risposta_parziale": response[-100:] + "..." # ultimi 100 caratteri
                            })
                    
                    show_debug("Risposta completa ricevuta", {
                        "lunghezza": len(response),
                        "chunks_totali": chunks_received,
                        "risposta": response[:200] + "..." # primi 200 caratteri
                    })
                    
                except Exception as e:
                    show_debug("ERRORE durante l'elaborazione", {
                        "tipo": type(e).__name__,
                        "messaggio": str(e),
                        "risposta_parziale": response
                    })
                    st.error(f"Errore durante l'elaborazione: {str(e)}")
            
            # Verifica e aggiunta risposta
            if response.strip():
                st.session_state.chats[st.session_state.current_chat]['messages'].append({
                    "role": "assistant",
                    "content": response
                })
                show_debug("Risposta aggiunta alla chat", "Successo")
            else:
                st.error("Risposta vuota ricevuta da Claude")
                show_debug("ERRORE", "Risposta vuota da Claude")
            
            show_debug("Stato finale messaggi", 
                      st.session_state.chats[st.session_state.current_chat]['messages'])


    def render(self):
        """Renderizza l'interfaccia chat con debug."""
        self.render_chat_controls()
        
        # Debug counter per i messaggi
        message_count = {
            "user": 0,
            "assistant": 0,
            "system": 0
        }
        
        messages_container = st.container()
        
        rendered_messages = set()
        
        current_chat = st.session_state.chats[st.session_state.current_chat]
        with messages_container:
            for idx, message in enumerate(current_chat['messages']):
                message_count[message['role']] += 1
                message_hash = hash(f"{idx}:{message['role']}:{message['content']}")
                
                if message_hash not in rendered_messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                        st.caption(f"Message ID: {idx} | Hash: {message_hash}")
                    rendered_messages.add(message_hash)
            
            # Mostra statistiche debug
            st.sidebar.markdown("### 📊 Debug Stats")
            st.sidebar.write({
                "Messaggi Utente": message_count["user"],
                "Risposte Claude": message_count["assistant"],
                "Messaggi Sistema": message_count["system"],
                "Totale Messaggi": sum(message_count.values()),
                "Messaggi Unici": len(rendered_messages)
            })

    def handle_user_input(self, prompt: str):
        """
        Gestisce l'input dell'utente in modo sicuro.
        """
        if not hasattr(st.session_state, 'processing'):
            st.session_state.processing = False
            
        if not st.session_state.processing and prompt:
            st.session_state.processing = True
            self.process_user_message(prompt)
            st.session_state.processing = False                

class CodeViewer:
    """Componente per la visualizzazione del codice."""
    
    def __init__(self):
        self.session = SessionManager()

    def render(self):
        """Renderizza il componente."""
        selected_file = st.session_state.get('selected_file')
        if selected_file and (file_info := st.session_state.uploaded_files.get(selected_file)):
            st.markdown(f"**{file_info['name']}** ({file_info['language']})")
            st.code(file_info['content'], language=file_info['language'])
        else:
            st.info("Select a file from the sidebar to view its content")

class ModelSelector:
    """Componente per la selezione del modello LLM."""
    
    def __init__(self):
        self.session = SessionManager()
    
    def render(self):
        """Renderizza il componente."""
        models = {
            'o1-mini': '🚀 O1 Mini (Fast)',
            'o1-preview': '🔍 O1 Preview (Advanced)',
            'claude-3-5-sonnet-20241022': '🎭 Claude 3.5 Sonnet (Detailed)'
        }
        
        current_model = self.session.get_current_model()
        selected = st.selectbox(
            " ",  # Spazio vuoto invece di "Select Model"
            list(models.keys()),
            format_func=lambda x: models[x],
            index=list(models.keys()).index(current_model),
            label_visibility="collapsed"  # Nasconde il label
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