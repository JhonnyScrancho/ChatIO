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
    def __init__(self):
        if 'messages' not in st.session_state:
            st.session_state.messages = []
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Ciao! Carica dei file e fammi delle domande su di essi. Posso aiutarti ad analizzarli."
            })

    def _get_file_content(self, filename: str) -> str:
        """Recupera il contenuto di un file."""
        if filename in st.session_state.uploaded_files:
            return st.session_state.uploaded_files[filename]['content']
        return None

    def render(self):
        """Renderizza l'interfaccia chat con layout corretto."""
        # Container principale con scrolling per i messaggi
        chat_container = st.container()
        
        # Container fisso per l'input
        input_container = st.container()

        # Stile CSS per fissare l'input in basso
        st.markdown("""
            <style>
                .stChatInput {
                    position: fixed;
                    bottom: 0;
                    left: 0;
                    right: 0;
                    background: white;
                    padding: 1rem;
                    z-index: 1000;
                    border-top: 1px solid #ddd;
                }
                
                .chat-message {
                    margin-bottom: 1rem;
                    padding-bottom: 1rem;
                    border-bottom: 1px solid #eee;
                }
                
                [data-testid="stVerticalBlock"] {
                    padding-bottom: 5rem;
                }
            </style>
        """, unsafe_allow_html=True)

        # Gestione input (deve essere prima del display dei messaggi)
        with input_container:
            if prompt := st.chat_input("Chiedi informazioni sui file..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                
                # Analizza i file quando viene fatta una domanda
                response = self._analyze_files(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response})

        # Display dei messaggi nella chat
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

    def _analyze_files(self, prompt: str) -> str:
        """Analizza i file in base alla domanda dell'utente."""
        if not st.session_state.uploaded_files:
            return "Non ho trovato file da analizzare. Carica prima alcuni file."

        # Prepara il contesto con tutti i file disponibili
        files_context = ""
        for filename, file_info in st.session_state.uploaded_files.items():
            content = file_info['content']
            files_context += f"\nFile: {filename}\n```\n{content}\n```\n"

        # Analizza il contenuto utilizzando il modello LLM configurato
        try:
            llm_manager = LLMManager()  # Assumiamo che sia già configurato
            
            # Prepara il prompt completo con il contesto dei file
            full_prompt = f"""Analizza i seguenti file in base alla domanda dell'utente:

{files_context}

Domanda dell'utente: {prompt}

Fornisci una risposta dettagliata analizzando il codice."""

            # Ottieni la risposta dal modello
            response = ""
            for chunk in llm_manager.process_request(prompt=full_prompt):
                response += chunk
            
            return response

        except Exception as e:
            return f"Mi dispiace, si è verificato un errore nell'analisi dei file: {str(e)}"

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