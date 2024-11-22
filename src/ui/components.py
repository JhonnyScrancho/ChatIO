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
    
    def process_single_file(self, uploaded_file) -> Optional[Dict]:
        """
        Processa un singolo file senza caching.
        
        Args:
            uploaded_file: File caricato da Streamlit
            
        Returns:
            Optional[Dict]: Informazioni sul file processato
        """
        if uploaded_file.size > 5 * 1024 * 1024:  # 5MB limit
            st.warning(f"File {uploaded_file.name} troppo grande. Massimo 5MB consentiti.")
            return None
            
        try:
            content = uploaded_file.read()
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # Determina il linguaggio
            extension = os.path.splitext(uploaded_file.name)[1].lower()
            language_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.html': 'html',
                '.css': 'css',
                '.java': 'java',
                '.cpp': 'cpp',
                '.c': 'c',
                '.md': 'markdown',
                '.txt': 'text',
                '.json': 'json',
                '.yml': 'yaml',
                '.yaml': 'yaml'
            }
            language = language_map.get(extension, 'text')
            
            # Highlight del codice
            try:
                lexer = get_lexer_for_filename(uploaded_file.name)
                formatter = HtmlFormatter(
                    style='monokai',
                    linenos=True,
                    cssclass='source'
                )
                highlighted = highlight(content, lexer, formatter)
            except:
                highlighted = f"<pre><code>{content}</code></pre>"
            
            return {
                'content': content,
                'language': language,
                'size': len(content),
                'name': uploaded_file.name,
                'highlighted': highlighted
            }
            
        except Exception as e:
            st.error(f"Errore nel processare {uploaded_file.name}: {str(e)}")
            return None
    
    def process_zip(self, zip_file) -> Dict[str, Dict]:
        """
        Processa un file ZIP.
        
        Args:
            zip_file: File ZIP caricato
            
        Returns:
            Dict[str, Dict]: Mappa dei file processati
        """
        processed_files = {}
        total_size = 0
        
        try:
            with ZipFile(BytesIO(zip_file.getvalue()), 'r') as zip_ref:
                for file_info in zip_ref.infolist():
                    if file_info.file_size > 5 * 1024 * 1024:  # 5MB per file
                        continue
                        
                    # Skip directories and hidden files
                    if file_info.filename.endswith('/') or '/.' in file_info.filename:
                        continue
                        
                    # Check extension
                    ext = os.path.splitext(file_info.filename)[1].lower()
                    if ext not in ['.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css',
                                 '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php',
                                 '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sh',
                                 '.sql', '.md', '.txt', '.json', '.yml', '.yaml']:
                        continue
                    
                    try:
                        content = zip_ref.read(file_info.filename).decode('utf-8')
                        file_data = {
                            'name': file_info.filename,
                            'content': content,
                            'size': file_info.file_size,
                            'language': os.path.splitext(file_info.filename)[1][1:],
                            'highlighted': None  # Will be generated on demand
                        }
                        processed_files[file_info.filename] = file_data
                        total_size += file_info.file_size
                        
                        if total_size > 15 * 1024 * 1024:  # 15MB total limit
                            break
                            
                    except Exception:
                        continue
                        
        except Exception as e:
            st.error(f"Errore nel processare il file ZIP: {str(e)}")
        
        return processed_files
    
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
                
                # Show stats
                with st.expander("📊 Stats"):
                    total_size = sum(f['size'] for f in files.values())
                    total_files = len(files)
                    languages = set(f['language'] for f in files.values())
                    
                    st.write(f"Total files: {total_files}")
                    st.write(f"Total size: {total_size / 1024:.1f} KB")
                    st.write(f"Languages: {', '.join(languages)}")

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
                
                # Prepariamo il contesto del file corrente
                current_file = self.session.get_current_file()
                file_content = None
                context = None
                if current_file:
                    file_info = self.session.get_file(current_file)
                    if file_info:
                        file_content = file_info['content']
                        context = f"File: {current_file} ({file_info['language']})"
                
                # Aggiungiamo la risposta dell'assistente alla history
                with chat_container.chat_message("assistant"):
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    for chunk in self.llm.process_request(
                        prompt=prompt,
                        analysis_type='code_review' if file_content else None,
                        file_content=file_content,
                        context=context
                    ):
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