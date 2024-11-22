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
        """Crea una struttura ad albero dai file."""
        tree = {}
        for path, content in files.items():
            current = tree
            parts = path.split('/')
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = content
        return tree

    def _render_tree_node(self, path: str, node: Dict[str, Any], prefix: str = "", is_last: bool = True):
        """Renderizza un nodo dell'albero dei file in stile minimale."""
        # Definisci i caratteri per l'albero
        PIPE = "│   "
        ELBOW = "└── "
        TEE = "├── "
        
        # Scegli il connettore appropriato
        connector = ELBOW if is_last else TEE
        
        if isinstance(node, dict) and 'content' not in node:
            # È una directory
            st.markdown(f"<div style='font-family: monospace; white-space: pre;'>{prefix}{connector}{path.split('/')[-1]}/</div>", 
                      unsafe_allow_html=True)
            
            items = sorted(node.items())
            for i, (name, child) in enumerate(items):
                is_last_item = i == len(items) - 1
                new_prefix = prefix + (PIPE if not is_last else "    ")
                self._render_tree_node(name, child, new_prefix, is_last_item)
        else:
            # È un file
            if st.button(f"{prefix}{connector}{path.split('/')[-1]}", 
                        key=f"file_{path}",
                        use_container_width=True,
                        type="secondary"):
                st.session_state.selected_file = path
                st.session_state.current_file = path

    def render(self):
        """Renderizza il componente."""
        uploaded_files = st.file_uploader(
            "Drag and drop files here",
            type=['py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'md', 'txt', 'json', 'yml', 'yaml', 'zip'],
            accept_multiple_files=True
        )

        if uploaded_files:
            for file in uploaded_files:
                try:
                    if file.name.endswith('.zip'):
                        import zipfile
                        import io
                        
                        zip_content = zipfile.ZipFile(io.BytesIO(file.read()))
                        for zip_file in zip_content.namelist():
                            if not zip_file.startswith('__') and not zip_file.startswith('.'):
                                try:
                                    content = zip_content.read(zip_file).decode('utf-8', errors='ignore')
                                    st.session_state.uploaded_files[zip_file] = {
                                        'content': content,
                                        'language': zip_file.split('.')[-1],
                                        'name': zip_file
                                    }
                                except Exception as e:
                                    continue
                    else:
                        content = file.read().decode('utf-8')
                        st.session_state.uploaded_files[file.name] = {
                            'content': content,
                            'language': file.name.split('.')[-1],
                            'name': file.name
                        }
                except Exception as e:
                    st.error(f"Errore nel processare {file.name}: {str(e)}")

        # Visualizza struttura ad albero
        if st.session_state.uploaded_files:
            st.markdown("""
                <style>
                    /* Stile per i bottoni dell'albero */
                    .stButton button {
                        background: none !important;
                        border: none !important;
                        padding: 0 !important;
                        font-family: monospace !important;
                        color: inherit !important;
                        text-align: left !important;
                        width: 100% !important;
                        margin: 0 !important;
                        height: auto !important;
                        line-height: 1.5 !important;
                    }
                    .stButton button:hover {
                        color: #ff4b4b !important;
                    }
                    /* Stile per il testo delle directory */
                    .directory {
                        color: #666;
                        font-family: monospace;
                    }
                </style>
            """, unsafe_allow_html=True)
            
            tree = self._create_file_tree(st.session_state.uploaded_files)
            st.markdown("<div style='font-family: monospace;'>allegro-io/</div>", unsafe_allow_html=True)
            items = sorted(tree.items())
            for i, (name, node) in enumerate(items):
                is_last = i == len(items) - 1
                self._render_tree_node(name, node, "", is_last)

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
            context = ""
            for filename, file_info in st.session_state.uploaded_files.items():
                context += f"\nFile: {filename}\n```{file_info['language']}\n{file_info['content']}\n```\n"

            response = ""
            with st.spinner("Analyzing code..."):
                for chunk in self.llm.process_request(
                    prompt=prompt,
                    context=context
                ):
                    response += chunk
            return response
        except Exception as e:
            return f"Mi dispiace, si è verificato un errore: {str(e)}"
        
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
                "Seleziona chat",
                options=list(st.session_state.chats.keys()),
                index=list(st.session_state.chats.keys()).index(st.session_state.current_chat)
            )
            if current_chat != st.session_state.current_chat:
                st.session_state.current_chat = current_chat

        with col2:
            # Pulsante nuova chat
            if st.button("🆕 Nuova", use_container_width=True):
                new_chat_name = f"Chat {len(st.session_state.chats) + 1}"
                st.session_state.chats[new_chat_name] = {
                    'messages': [],
                    'created_at': datetime.now().isoformat()
                }
                st.session_state.current_chat = new_chat_name
                st.rerun()

        with col3:
            # Pulsante rinomina
            if st.button("✏️ Rinomina", use_container_width=True):
                st.session_state.renaming = True
                st.rerun()

        with col4:
            # Pulsante elimina
            if len(st.session_state.chats) > 1 and st.button("🗑️ Elimina", use_container_width=True):
                if st.session_state.current_chat in st.session_state.chats:
                    del st.session_state.chats[st.session_state.current_chat]
                    st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                    st.rerun()

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
                        st.rerun()
                with col2:
                    if st.form_submit_button("Annulla"):
                        st.session_state.renaming = False
                        st.rerun()    

    def render(self):
        """Renderizza l'interfaccia chat."""
        # Renderizza i controlli delle chat
        self.render_chat_controls()
        
        # Container per i messaggi della chat corrente
        messages_container = st.container()
        
        current_chat = st.session_state.chats[st.session_state.current_chat]
        with messages_container:
            for message in current_chat['messages']:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

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
            "Select Model",
            list(models.keys()),
            format_func=lambda x: models[x],
            index=list(models.keys()).index(current_model)
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