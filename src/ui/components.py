"""
UI components for Allegro IO Code Assistant.
"""

import streamlit as st
from src.core.session import SessionManager
from src.core.files import FileManager
from src.core.llm import LLMManager

import streamlit as st
from typing import Dict, Any

class FileExplorer:
    """Component per l'esplorazione e l'upload dei file."""
    
    def __init__(self):
        """Inizializza il componente."""
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = {}
    
    def _render_tree_node(self, path: str, node: Dict[str, Any], indent: int = 0):
        """Renderizza un nodo dell'albero dei file."""
        if isinstance(node, dict) and 'content' not in node:
            # È una directory
            st.markdown(f"{'&nbsp;' * (indent * 2)}📁 **{path.split('/')[-1]}**", unsafe_allow_html=True)
            for name, child in sorted(node.items()):
                self._render_tree_node(f"{path}/{name}", child, indent + 1)
        else:
            # È un file
            icon = self._get_file_icon(path)
            if st.button(f"{'    ' * indent}{icon} {path.split('/')[-1]}", key=f"file_{path}"):
                st.session_state.selected_file = path
    
    def _get_file_icon(self, filename: str) -> str:
        """Restituisce l'icona appropriata per il tipo di file."""
        ext = filename.split('.')[-1].lower() if '.' in filename else ''
        icons = {
            'py': '🐍',
            'js': '📜',
            'html': '🌐',
            'css': '🎨',
            'md': '📝',
            'txt': '📄',
            'json': '📋',
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

    def render(self):
        """Renderizza il componente."""
        # File uploader
        uploaded_files = st.file_uploader(
            "Upload files",
            type=['py', 'js', 'html', 'css', 'txt', 'md', 'json', 'zip'],
            accept_multiple_files=True
        )

        if uploaded_files:
            for file in uploaded_files:
                try:
                    if file.name.endswith('.zip'):
                        import zipfile
                        import io
                        
                        # Processa il file ZIP
                        zip_content = zipfile.ZipFile(io.BytesIO(file.read()))
                        for zip_file in zip_content.namelist():
                            if not zip_file.startswith('__') and not zip_file.startswith('.'):
                                content = zip_content.read(zip_file).decode('utf-8', errors='ignore')
                                st.session_state.uploaded_files[zip_file] = {
                                    'content': content,
                                    'type': zip_file.split('.')[-1]
                                }
                    else:
                        # Processa file singolo
                        content = file.read().decode('utf-8')
                        st.session_state.uploaded_files[file.name] = {
                            'content': content,
                            'type': file.name.split('.')[-1]
                        }
                except Exception as e:
                    st.error(f"Errore nel processare {file.name}: {str(e)}")

        # Visualizza struttura ad albero
        if st.session_state.uploaded_files:
            st.markdown("### Files")
            tree = self._create_file_tree(st.session_state.uploaded_files)
            for name, node in sorted(tree.items()):
                self._render_tree_node(name, node)

class ChatInterface:
    """Component per l'interfaccia chat."""
    
    def __init__(self):
        self.session = SessionManager()
        self.llm = LLMManager()
    
    def render(self):
        # Container per la chat history con scrolling
        chat_container = st.container()
        
        # Input container fissato in basso
        input_container = st.container()
        
        # Gestiamo prima l'input per mantenere il flusso corretto
        with input_container:
            st.write("")  # Spacer
            st.markdown("""
                <style>
                    .stChatInput {
                        position: fixed;
                        bottom: 3rem;
                        background: white;
                        padding: 1rem 0;
                        z-index: 100;
                    }
                </style>
            """, unsafe_allow_html=True)
            if prompt := st.chat_input("Ask about your code..."):
                # Aggiungiamo il messaggio dell'utente alla history
                self.session.add_to_chat_history({
                    "role": "user",
                    "content": prompt
                })
                
                # Prepariamo il prompt con il contenuto del file corrente
                current_file = self.session.get_current_file()
                file_content = None
                if current_file:
                    file_info = self.session.get_file(current_file)
                    if file_info:
                        file_content = file_info['content']
                
                full_prompt = prompt
                if file_content:
                    full_prompt = f"{prompt}\n\nFile content:\n```\n{file_content}\n```"
                
                # Aggiungiamo la risposta dell'assistente alla history
                with chat_container.chat_message("assistant"):
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    for chunk in self.llm.process_request(prompt=full_prompt):
                        full_response += chunk
                        message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
                
                self.session.add_to_chat_history({
                    "role": "assistant",
                    "content": full_response
                })
        
        # Mostra la chat history nel container principale
        with chat_container:
            for msg in self.session.get_chat_history():
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
            
            # Aggiungiamo spazio extra in fondo per l'input
            st.write("")
            st.write("")
            st.write("")

class CodeViewer:
    """Component per la visualizzazione del codice."""
    
    def __init__(self):
        self.session = SessionManager()
    
    def render(self):
        current_file = self.session.get_current_file()
        if current_file and (file_info := self.session.get_file(current_file)):
            st.markdown(f"**{file_info['name']}** ({file_info['language']})")
            st.markdown(file_info['highlighted'], unsafe_allow_html=True)

class ModelSelector:
    """Component per la selezione del modello LLM."""
    
    def __init__(self):
        self.session = SessionManager()
    
    def render(self):
        models = {
            'o1-mini': '🚀 O1 Mini (Fast)',
            'o1-preview': '🔍 O1 Preview (Advanced)',
            'claude-3-5-sonnet': '🎭 Claude 3.5 Sonnet (Detailed)'
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
    """Component per la visualizzazione delle statistiche."""
    
    def __init__(self):
        self.session = SessionManager()
    
    def render(self):
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