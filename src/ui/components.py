"""
UI components for Allegro IO Code Assistant.
"""

import streamlit as st
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

    def _render_tree_node(self, path: str, node: Dict[str, Any], indent: int = 0):
        """Renderizza un nodo dell'albero dei file."""
        if isinstance(node, dict) and 'content' not in node:
            # È una directory
            st.markdown(f"""
                <div class="file-tree-folder" style="margin-left: {indent*10}px">
                    <span>📁 {path.split('/')[-1]}</span>
                </div>
            """, unsafe_allow_html=True)
            for name, child in sorted(node.items()):
                self._render_tree_node(f"{path}/{name}", child, indent + 1)
        else:
            # È un file
            icon = self._get_file_icon(path)
            if st.button(
                f"{'    ' * indent}{icon} {path.split('/')[-1]}", 
                key=f"file_{path}",
                use_container_width=True
            ):
                st.session_state.selected_file = path
                st.session_state.current_file = path

    def render(self):
        """Renderizza l'interfaccia chat."""
        # CSS aggiornato con i selettori corretti
        st.markdown("""
            <style>
                /* Container principale della chat */
                div[data-testid="stVerticalBlockBorderWrapper"] {
                    position: fixed !important;
                    bottom: 0 !important;
                    left: 18rem !important;  /* Sidebar width */
                    right: 2rem !important;
                    background: white !important;
                    padding: 1rem !important;
                    z-index: 999999 !important;
                    border-top: 1px solid #ddd !important;
                }
                
                /* Contenitore dell'input */
                .stChatInput {
                    margin-bottom: 0 !important;
                }
                
                /* Area messaggi con padding per l'input */
                [data-testid="stChatMessageContainer"] {
                    margin-bottom: 80px !important;
                    padding-bottom: 40px !important;
                }
                
                /* Nasconde il footer */
                footer {
                    display: none !important;
                }
                
                /* Assicura che il contenitore principale abbia spazio per l'input */
                .main .block-container {
                    padding-bottom: 100px !important;
                }
                
                /* Style per i messaggi */
                .stChatMessage {
                    margin-bottom: 1rem !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Container per i messaggi
        chat_container = st.container()
        
        # Visualizza i messaggi
        with chat_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Input 
        if prompt := st.chat_input("Ask about your code...", key="chat_input"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.spinner("Processing..."):
                response = self._process_response(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response})

class ChatInterface:
    """Componente per l'interfaccia chat."""
    
    def __init__(self):
        self.session = SessionManager()
        self.llm = LLMManager()
        if 'messages' not in st.session_state:
            st.session_state.messages = []
            st.session_state.messages.append({
                "role": "assistant",
                "content": "Ciao! Carica dei file e fammi delle domande su di essi. Posso aiutarti ad analizzarli."
            })

    def _process_response(self, prompt: str) -> str:
        """Processa la richiesta e genera una risposta."""
        try:
            # Prepara il contesto con i file disponibili
            context = ""
            for filename, file_info in st.session_state.uploaded_files.items():
                context += f"\nFile: {filename}\n```{file_info['language']}\n{file_info['content']}\n```\n"

            # Genera la risposta
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

    def render(self):
        """Renderizza l'interfaccia chat."""
        # CSS per fissare l'input in basso
        st.markdown("""
            <style>
                /* Nasconde il footer standard di Streamlit */
                footer {display: none !important;}
                
                /* Contenitore principale della chat */
                .stChatFloatingInputContainer, .stChatInputContainer {
                    position: fixed !important;
                    bottom: 0 !important;
                    background: white !important;
                    padding: 1rem !important;
                    border-top: 1px solid #ddd !important;
                    z-index: 999999 !important;
                    left: 18rem !important; /* Larghezza della sidebar */
                    right: 0 !important;
                }
                
                /* Aggiunge spazio in fondo per evitare che i messaggi vengano nascosti dall'input */
                [data-testid="stChatMessageContainer"] {
                    padding-bottom: 100px !important;
                }
                
                .main .block-container {
                    padding-bottom: 100px !important;
                }
                
                /* Stile per i messaggi della chat */
                .stChatMessage {
                    background: white !important;
                    border: 1px solid #ddd !important;
                    border-radius: 5px !important;
                    margin-bottom: 0.5rem !important;
                    padding: 0.5rem !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        # Contenitore per i messaggi con padding extra in fondo
        messages_container = st.container()
        
        # Input container separato che verrà fissato dal CSS
        input_container = st.container()
        
        # Renderizza i messaggi
        with messages_container:
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Renderizza l'input
        with input_container:
            if prompt := st.chat_input("Ask about your code...", key="chat_input"):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.spinner("Processing..."):
                    response = self._process_response(prompt)
                    st.session_state.messages.append({"role": "assistant", "content": response})

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