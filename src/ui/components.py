"""
UI components for Allegro IO Code Assistant.
"""

import streamlit as st
from src.core.session import SessionManager
from src.core.files import FileManager
from src.core.llm import LLMManager

class FileExplorer:
    """Component per l'esplorazione e l'upload dei file."""
    
    def __init__(self):
        self.session = SessionManager()
        self.file_manager = FileManager()
    
    def render(self):
        uploaded_files = st.file_uploader(
            "Upload Files",
            accept_multiple_files=True,
            type=[ext[1:] for ext in self.file_manager.ALLOWED_EXTENSIONS]
        )
        
        if uploaded_files:
            for file in uploaded_files:
                if file.name.endswith('.zip'):
                    files = self.file_manager.process_zip(file)
                    for name, info in files.items():
                        self.session.add_file(name, info)
                else:
                    result = self.file_manager.process_file(file)
                    if result:
                        self.session.add_file(file.name, result)
            
            # File Tree View
            st.markdown("### 📂 Files")
            files = self.session.get_all_files()
            if files:
                tree = self.file_manager.create_file_tree(files)
                self._render_tree(tree)
                
                # Mostra statistiche
                stats = self.file_manager.analyze_codebase(files)
                with st.expander("📊 Codebase Stats"):
                    st.write(f"Total Files: {stats['total_files']}")
                    st.write(f"Total Lines: {stats['line_count']:,}")
                    st.write(f"Total Size: {stats['total_size'] / 1024:.1f} KB")
                    st.write("Languages:", ", ".join(f"{k} ({v})" for k, v in stats['languages'].items()))
    
    def _render_tree(self, tree, indent=0):
        """Renderizza la struttura ad albero dei file."""
        for name, value in tree.items():
            if isinstance(value, dict):
                if '_info' in value:  # È un file
                    icon = self.file_manager.get_file_icon(name)
                    if st.button(f"{'  ' * indent}{icon} {name}", key=f"file_{name}"):
                        self.session.set_current_file(name)
                else:  # È una directory
                    st.markdown(f"{'  ' * indent}📁 {name}")
                    self._render_tree(value, indent + 1)

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