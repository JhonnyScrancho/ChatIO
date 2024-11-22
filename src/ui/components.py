"""
UI components for Allegro IO Code Assistant.
"""

import os
import streamlit as st
from typing import Dict, Optional, Any
from zipfile import ZipFile
from io import BytesIO
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter

from src.core.session import SessionManager
from src.core.files import FileManager
from src.core.llm import LLMManager

class FileExplorer:
    """Component per l'esplorazione e l'upload dei file."""
    
    def __init__(self):
        self.session = SessionManager()
        self.file_manager = FileManager()
    
    def process_single_file(self, uploaded_file) -> Optional[Dict[str, Any]]:
        """
        Processa un singolo file senza caching.
        
        Args:
            uploaded_file: File caricato da Streamlit
            
        Returns:
            Optional[Dict[str, Any]]: Informazioni sul file processato
        """
        return self.file_manager.process_file(uploaded_file)
    
    def process_zip(self, zip_file) -> Dict[str, Dict[str, Any]]:
        """
        Processa un file ZIP.
        
        Args:
            zip_file: File ZIP caricato
            
        Returns:
            Dict[str, Dict[str, Any]]: Mappa dei file processati
        """
        return self.file_manager.process_zip(zip_file)
    
    def render(self):
        """Renderizza il componente FileExplorer."""
        uploaded_files = st.file_uploader(
            "Upload Files",
            accept_multiple_files=True,
            type=['py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css',
                  'java', 'cpp', 'c', 'h', 'hpp', 'cs', 'php',
                  'rb', 'go', 'rs', 'swift', 'kt', 'scala', 'sh',
                  'sql', 'md', 'txt', 'json', 'yml', 'yaml', 'zip']
        )
        
        if uploaded_files:
            for file in uploaded_files:
                if file.type == "application/zip" or file.name.endswith('.zip'):
                    with st.spinner(f"Processing ZIP file {file.name}..."):
                        files = self.process_zip(file)
                        for name, info in files.items():
                            self.session.add_file(name, info)
                else:
                    with st.spinner(f"Processing file {file.name}..."):
                        result = self.process_single_file(file)
                        if result:
                            self.session.add_file(file.name, result)
            
            # Show file tree
            files = self.session.get_all_files()
            if files:
                st.markdown("### 📂 Files")
                for filename, file_info in files.items():
                    if st.button(f"📄 {filename}", key=f"file_{filename}"):
                        self.session.set_current_file(filename)

class ChatInterface:
    """Component per l'interfaccia chat."""
    
    def __init__(self):
        self.session = SessionManager()
        self.llm = LLMManager()
    
    def render(self):
        """Renderizza l'interfaccia chat."""
        # Chat history container
        chat_container = st.container()
        
        # Input area
        prompt = st.text_area("Ask about your code...", key="chat_input")
        if st.button("Send", key="send_button"):
            if prompt:
                # Add user message to history
                self.session.add_to_chat_history({
                    "role": "user",
                    "content": prompt
                })
                
                # Get current file context
                current_file = self.session.get_current_file()
                file_content = None
                context = None
                if current_file:
                    file_info = self.session.get_file(current_file)
                    if file_info:
                        file_content = file_info['content']
                        context = f"File: {current_file} ({file_info['language']})"
                
                # Process response
                with st.spinner("Thinking..."):
                    response = ""
                    for chunk in self.llm.process_request(
                        prompt=prompt,
                        file_content=file_content,
                        context=context
                    ):
                        response += chunk
                        
                    # Add assistant response to history
                    self.session.add_to_chat_history({
                        "role": "assistant",
                        "content": response
                    })
        
        # Display chat history
        with chat_container:
            for msg in self.session.get_chat_history():
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

class CodeViewer:
    """Component per la visualizzazione del codice."""
    
    def __init__(self):
        self.session = SessionManager()
    
    def render(self):
        """Renderizza il visualizzatore di codice."""
        current_file = self.session.get_current_file()
        if current_file and (file_info := self.session.get_file(current_file)):
            st.markdown(f"**{current_file}** ({file_info['language']})")
            st.markdown(file_info['highlighted'], unsafe_allow_html=True)

class ModelSelector:
    """Component per la selezione del modello LLM."""
    
    def __init__(self):
        self.session = SessionManager()
    
    def render(self):
        """Renderizza il selettore del modello."""
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
        """Renderizza il display delle statistiche."""
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