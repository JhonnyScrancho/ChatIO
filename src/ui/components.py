"""
UI components for Allegro IO Code Assistant.
"""

import streamlit as st
from ..core import SessionManager, FileManager, LLMManager

class FileExplorer:
    """Component per l'esplorazione e l'upload dei file."""
    
    def __init__(self):
        self.session = SessionManager()
        self.file_manager = FileManager()
    
    def render(self):
        uploaded_files = st.file_uploader(
            "Upload Files",
            accept_multiple_files=True,
            type=list(FileManager.ALLOWED_EXTENSIONS)
        )
        
        if uploaded_files:
            for file in uploaded_files:
                if file.name.endswith('.zip'):
                    files = self.file_manager.process_zip(file)
                    for name, (content, lang, size) in files.items():
                        self.session.add_file(name, (content, lang, size))
                else:
                    content, lang, size = self.file_manager.process_file(file)
                    self.session.add_file(file.name, (content, lang, size))
            
            # File Tree View
            st.markdown("### 📂 Files")
            files = {k: v[0] for k, v in st.session_state.files.items()}
            tree = self.file_manager.create_file_tree(files)
            self._render_tree(tree)
    
    def _render_tree(self, tree, indent=0):
        """Renderizza la struttura ad albero dei file."""
        for name, value in tree.items():
            if isinstance(value, dict):
                st.markdown(f"{'  ' * indent}📁 {name}")
                self._render_tree(value, indent + 1)
            else:
                icon = self.file_manager.get_file_icon(name)
                if st.button(f"{'  ' * indent}{icon} {name}", key=value):
                    self.session.set_current_file(value)

class ChatInterface:
    """Component per l'interfaccia chat."""
    
    def __init__(self):
        self.session = SessionManager()
        self.llm = LLMManager()
    
    def render(self):
        # Chat History
        for msg in self.session.get_chat_history():
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        
        # Input
        if prompt := st.chat_input("Chiedi qualcosa sul tuo codice..."):
            # User Message
            with st.chat_message("user"):
                st.markdown(prompt)
            self.session.add_to_chat_history({
                "role": "user",
                "content": prompt
            })
            
            # Assistant Response
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""
                
                # Stream response
                for chunk in self.llm.process_request(prompt):
                    full_response += chunk
                    message_placeholder.markdown(full_response + "▌")
                message_placeholder.markdown(full_response)
            
            self.session.add_to_chat_history({
                "role": "assistant",
                "content": full_response
            })

class CodeViewer:
    """Component per la visualizzazione del codice."""
    
    def __init__(self):
        self.session = SessionManager()
        self.file_manager = FileManager()
    
    def render(self):
        current_file = self.session.get_current_file()
        if current_file and (file_data := self.session.get_file(current_file)):
            content, lang, _ = file_data
            highlighted = self.file_manager.highlight_code(content, lang)
            st.markdown(f"**{current_file}** ({lang})")
            st.markdown(highlighted, unsafe_allow_html=True)
            
            # Add CSS for syntax highlighting
            st.markdown("""
                <style>
                    .source { background-color: #272822; padding: 10px; border-radius: 5px; }
                    .source .linenos { color: #8f908a; padding-right: 10px; }
                    .source pre { margin: 0; }
                </style>
                """, unsafe_allow_html=True)

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