"""
UI component for file exploration and management in Streamlit.
"""

import streamlit as st
from typing import Dict, Any
import os
from io import BytesIO
from zipfile import ZipFile
from pygments import highlight
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.formatters import HtmlFormatter

class FileExplorer:
    """A simplified file explorer component for Streamlit."""
    
    ALLOWED_EXTENSIONS = {
        '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css',
        '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php',
        '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.sh',
        '.sql', '.md', '.txt', '.json', '.yml', '.yaml'
    }
    
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    
    def __init__(self):
        """Initialize the FileExplorer component."""
        # Initialize session state if needed
        if 'files' not in st.session_state:
            st.session_state.files = {}
        if 'selected_file' not in st.session_state:
            st.session_state.selected_file = None

    def _process_file_content(self, content: str, filename: str) -> Dict[str, Any]:
        """Process the content of a file."""
        try:
            lexer = get_lexer_for_filename(filename)
            language = lexer.name.lower()
        except:
            language = 'text'
            lexer = TextLexer()
            
        formatter = HtmlFormatter(
            style='monokai',
            linenos=True,
            cssclass='source'
        )
        
        highlighted = highlight(content, lexer, formatter)
        
        return {
            'content': content,
            'language': language,
            'name': filename,
            'highlighted': highlighted,
            'size': len(content)
        }

    def _get_file_icon(self, filename: str) -> str:
        """Get an appropriate icon for the file type."""
        ext = os.path.splitext(filename)[1].lower()
        icons = {
            '.py': '🐍',
            '.js': '📜',
            '.jsx': '⚛️',
            '.ts': '📘',
            '.tsx': '💠',
            '.html': '🌐',
            '.css': '🎨',
            '.md': '📝',
            '.txt': '📄',
            '.json': '📋',
            '.yml': '⚙️',
            '.yaml': '⚙️',
            '.zip': '📦'
        }
        return icons.get(ext, '📄')

    def render(self):
        """Render the file explorer component."""
        st.markdown("""
            <style>
                .file-button {
                    text-align: left;
                    padding: 0.5rem;
                    margin: 0.2rem 0;
                }
                .file-button:hover {
                    background-color: rgba(255, 255, 255, 0.1);
                }
            </style>
        """, unsafe_allow_html=True)

        uploaded_files = st.file_uploader(
            "Upload Files",
            type=[ext[1:] for ext in self.ALLOWED_EXTENSIONS],
            accept_multiple_files=True,
            key="file_uploader"
        )

        if uploaded_files:
            for file in uploaded_files:
                try:
                    if file.name.endswith('.zip'):
                        with ZipFile(BytesIO(file.read()), 'r') as zip_ref:
                            for zip_file in zip_ref.namelist():
                                if (not zip_file.startswith('__') and 
                                    not zip_file.startswith('.') and 
                                    not zip_file.endswith('/')):
                                    try:
                                        content = zip_ref.read(zip_file).decode('utf-8', errors='ignore')
                                        if len(content) <= self.MAX_FILE_SIZE:
                                            processed_file = self._process_file_content(content, zip_file)
                                            st.session_state.files[zip_file] = processed_file
                                    except Exception as e:
                                        st.warning(f"Error processing {zip_file}: {str(e)}")
                    else:
                        content = file.read().decode('utf-8')
                        if len(content) <= self.MAX_FILE_SIZE:
                            processed_file = self._process_file_content(content, file.name)
                            st.session_state.files[file.name] = processed_file
                except Exception as e:
                    st.error(f"Error processing {file.name}: {str(e)}")

        # Display uploaded files
        if st.session_state.files:
            st.markdown("### 📁 Uploaded Files")
            for filename, file_info in st.session_state.files.items():
                icon = self._get_file_icon(filename)
                if st.button(
                    f"{icon} {filename}",
                    key=f"file_{filename}",
                    use_container_width=True,
                    type="secondary"
                ):
                    st.session_state.selected_file = filename

        # Display selected file content
        if st.session_state.selected_file:
            file_info = st.session_state.files[st.session_state.selected_file]
            st.markdown("---")
            st.markdown(f"### 📄 {file_info['name']}")
            st.code(file_info['content'], language=file_info['language'])

class ChatInterface:
    """Componente per l'interfaccia chat."""
    
    def __init__(self):
        if 'chats' not in st.session_state:
            st.session_state.chats = {
                'Chat principale': {
                    'messages': [{
                        "role": "assistant",
                        "content": "Ciao! Carica dei file e fammi delle domande su di essi."
                    }],
                    'created_at': datetime.now().isoformat()
                }
            }
            st.session_state.current_chat = 'Chat principale'

    def _format_file_preview(self, file_info):
        """Formatta l'anteprima del file per la chat."""
        preview_length = min(200, len(file_info['content']))
        return f"""```{file_info['language']}
{file_info['content'][:preview_length]}{'...' if preview_length < len(file_info['content']) else ''}
```
[File: {file_info['name']} - {len(file_info['content'])} bytes]"""

    def _get_files_context(self):
        """Recupera il contesto dei file per la chat."""
        if not st.session_state.files:
            return None
            
        files_preview = []
        for filename, file_info in st.session_state.files.items():
            files_preview.append(self._format_file_preview(file_info))
            
        return "\n".join([
            "📁 Files caricati:",
            *files_preview
        ])

    def render_chat_controls(self):
        """Renderizza i controlli per la gestione delle chat."""
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            current_chat = st.selectbox(
                "Chat attiva",
                options=list(st.session_state.chats.keys()),
                index=list(st.session_state.chats.keys()).index(st.session_state.current_chat)
            )
            if current_chat != st.session_state.current_chat:
                st.session_state.current_chat = current_chat

        with col2:
            if st.button("🆕 Nuova", use_container_width=True):
                new_chat_name = f"Chat {len(st.session_state.chats) + 1}"
                st.session_state.chats[new_chat_name] = {
                    'messages': [],
                    'created_at': datetime.now().isoformat()
                }
                st.session_state.current_chat = new_chat_name
                st.rerun()

        with col3:
            if st.button("✏️ Rinomina", use_container_width=True):
                st.session_state.renaming = True
                st.rerun()

        with col4:
            if len(st.session_state.chats) > 1 and st.button("🗑️ Elimina", use_container_width=True):
                if st.session_state.current_chat in st.session_state.chats:
                    del st.session_state.chats[st.session_state.current_chat]
                    st.session_state.current_chat = list(st.session_state.chats.keys())[0]
                    st.rerun()

    def render(self):
        """Renderizza l'interfaccia chat."""
        # Stili per il container dei messaggi
        st.markdown("""
            <style>
                div[data-testid="stChatMessageContainer"] {
                    min-height: calc(100vh - 200px);
                    padding-bottom: 100px;
                    overflow-y: auto;
                }
                
                div[data-testid="stChatMessage"] {
                    max-width: none !important;
                    width: auto !important;
                    margin: 1rem 0 !important;
                }
                
                /* Stile per il codice nei messaggi */
                .stMarkdown pre {
                    max-height: 400px;
                    overflow-y: auto;
                }
            </style>
        """, unsafe_allow_html=True)

        # Renderizza i controlli delle chat
        self.render_chat_controls()

        # Gestione rinomina chat
        if getattr(st.session_state, 'renaming', False):
            with st.form("rename_chat_form"):
                new_name = st.text_input("Nuovo nome", value=st.session_state.current_chat)
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Salva"):
                        if new_name and new_name != st.session_state.current_chat:
                            st.session_state.chats[new_name] = st.session_state.chats.pop(st.session_state.current_chat)
                            st.session_state.current_chat = new_name
                        st.session_state.renaming = False
                        st.rerun()
                with col2:
                    if st.form_submit_button("Annulla"):
                        st.session_state.renaming = False
                        st.rerun()
        
        # Messages container
        messages_container = st.container()
        
        # Mostra i messaggi della chat corrente
        with messages_container:
            for message in st.session_state.chats[st.session_state.current_chat]['messages']:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    
                    # Se è un messaggio dell'assistente, mostra opzioni
                    if message["role"] == "assistant":
                        with st.expander("🔧 Opzioni", expanded=False):
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("📋 Copia", key=f"copy_{hash(message['content'])}"):
                                    import pyperclip
                                    pyperclip.copy(message['content'])
                                    st.success("Copiato!")
                            with col2:
                                if st.button("🔄 Rigenera", key=f"regen_{hash(message['content'])}"):
                                    # Trova l'ultimo messaggio utente
                                    user_messages = [msg for msg in st.session_state.chats[st.session_state.current_chat]['messages'] 
                                                   if msg["role"] == "user"]
                                    if user_messages:
                                        last_user_message = user_messages[-1]["content"]
                                        # Rigenera la risposta
                                        with st.spinner("Rigenerazione in corso..."):
                                            context = ""
                                            if st.session_state.files:
                                                for filename, file_info in st.session_state.files.items():
                                                    context += f"\nFile: {filename}\n```{file_info['language']}\n{file_info['content']}\n```\n"
                                            
                                            from src.core.llm import LLMManager
                                            llm = LLMManager()
                                            new_response = ""
                                            for chunk in llm.process_request(
                                                prompt=last_user_message,
                                                context=context
                                            ):
                                                new_response += chunk
                                            
                                            # Sostituisci il messaggio
                                            message['content'] = new_response
                                            st.rerun()

class CodeViewer:
    """Componente per la visualizzazione del codice."""
    
    def render(self):
        """Renderizza il componente."""
        selected_file = st.session_state.get('selected_file')
        if selected_file and (file_info := st.session_state.uploaded_files.get(selected_file)):
            st.markdown(f"**{file_info['name']}** ({file_info['language']})")
            st.code(file_info['content'], language=file_info['language'])
            
            # Stats
            st.markdown("---")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Linee di codice", len(file_info['content'].splitlines()))
            with col2:
                st.metric("Dimensione", f"{len(file_info['content'])} bytes")
        else:
            st.info("Seleziona un file dalla sidebar per visualizzarlo")

class ModelSelector:
    """Componente per la selezione del modello LLM."""
    
    def render(self):
        """Renderizza il componente."""
        models = {
            'o1-mini': '🚀 O1 Mini (Fast)',
            'o1-preview': '🔍 O1 Preview (Advanced)',
            'claude-3-5-sonnet-20241022': '🎭 Claude 3.5 Sonnet (Detailed)'
        }
        
        current_model = st.session_state.get('current_model', 'o1-mini')
        selected = st.selectbox(
            "Modello",
            list(models.keys()),
            format_func=lambda x: models[x],
            index=list(models.keys()).index(current_model)
        )
        
        if selected != current_model:
            st.session_state.current_model = selected
            
        # Mostra info sul modello
        if st.checkbox("Mostra dettagli modello"):
            model_info = {
                'o1-mini': {
                    'context': '128K tokens',
                    'best_for': 'Quick fixes, simple analysis',
                    'cost': '$0.001/1K tokens'
                },
                'o1-preview': {
                    'context': '128K tokens',
                    'best_for': 'Complex analysis, architecture review',
                    'cost': '$0.01/1K tokens'
                },
                'claude-3-5-sonnet-20241022': {
                    'context': '200K tokens',
                    'best_for': 'Large codebases, detailed explanations',
                    'cost': '$0.008/1K tokens'
                }
            }
            
            info = model_info[selected]
            st.markdown(f"""
            **Dettagli Modello:**
            - Contesto: {info['context']}
            - Ideale per: {info['best_for']}
            - Costo: {info['cost']}
            """)

class StatsDisplay:
    """Componente per la visualizzazione delle statistiche."""
    
    def _format_number(self, num: float) -> str:
        """Formatta un numero per la visualizzazione."""
        if num >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num/1_000:.1f}K"
        return str(int(num))

    def _get_token_trend(self) -> float:
        """Calcola il trend dei token utilizzati."""
        if 'token_history' not in st.session_state:
            st.session_state.token_history = []
        
        history = st.session_state.token_history
        if len(history) >= 2:
            return ((history[-1] - history[-2]) / history[-2]) * 100 if history[-2] != 0 else 0
        return 0

    def render(self):
        """Renderizza il componente."""
        # Aggiorna la storia dei token
        if 'token_history' not in st.session_state:
            st.session_state.token_history = []
        st.session_state.token_history.append(st.session_state.get('token_count', 0))
        if len(st.session_state.token_history) > 10:
            st.session_state.token_history.pop(0)

        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Token utilizzati",
                self._format_number(st.session_state.get('token_count', 0)),
                delta=f"{self._get_token_trend():.1f}%",
                delta_color="inverse"
            )
        
        with col2:
            st.metric(
                "Costo ($)",
                f"${st.session_state.get('cost', 0.0):.3f}",
                delta=None
            )
        
        with col3:
            st.metric(
                "File analizzati",
                len(st.session_state.get('files', {})),
                delta=None
            )
            
        if st.checkbox("Mostra statistiche dettagliate"):
            st.markdown("### 📊 Statistiche dettagliate")
            
            # Statistiche per tipo di file
            file_types = {}
            for file_info in st.session_state.get('files', {}).values():
                lang = file_info['language']
                file_types[lang] = file_types.get(lang, 0) + 1
            
            if file_types:
                st.markdown("#### Distribuzione tipi di file")
                for lang, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True):
                    st.progress(count / len(st.session_state['files']), text=f"{lang}: {count}")
            
            # Utilizzo del modello
            st.markdown("#### Utilizzo modelli")
            if 'model_usage' not in st.session_state:
                st.session_state.model_usage = {
                    'o1-mini': 0,
                    'o1-preview': 0,
                    'claude-3-5-sonnet-20241022': 0
                }
            
            for model, count in st.session_state.model_usage.items():
                st.progress(
                    count / (sum(st.session_state.model_usage.values()) or 1),
                    text=f"{model}: {count} richieste"
                )

class FileAnalyzer:
    """Componente per l'analisi dei file."""
    
    def _count_lines_by_type(self, content: str) -> Dict[str, int]:
        """Conta le linee per tipo (codice, commenti, vuote)."""
        lines = content.split('\n')
        stats = {
            'code': 0,
            'comments': 0,
            'blank': 0
        }
        
        in_multiline_comment = False
        for line in lines:
            line = line.strip()
            
            if not line:
                stats['blank'] += 1
            elif line.startswith(('/*', '/**')) and '*/' not in line:
                in_multiline_comment = True
                stats['comments'] += 1
            elif '*/' in line and in_multiline_comment:
                in_multiline_comment = False
                stats['comments'] += 1
            elif in_multiline_comment:
                stats['comments'] += 1
            elif line.startswith(('#', '//', '<!--')):
                stats['comments'] += 1
            else:
                stats['code'] += 1
                
        return stats

    def _analyze_complexity(self, content: str, language: str) -> Dict[str, Any]:
        """Analizza la complessità del codice."""
        metrics = {
            'functions': 0,
            'classes': 0,
            'imports': 0,
            'max_line_length': 0,
            'avg_line_length': 0
        }
        
        lines = content.split('\n')
        total_length = 0
        
        for line in lines:
            # Line length metrics
            line_length = len(line)
            metrics['max_line_length'] = max(metrics['max_line_length'], line_length)
            total_length += line_length
            
            # Language specific metrics
            if language == 'python':
                if 'def ' in line:
                    metrics['functions'] += 1
                elif 'class ' in line:
                    metrics['classes'] += 1
                elif 'import ' in line or 'from ' in line and ' import ' in line:
                    metrics['imports'] += 1
            elif language in ['javascript', 'typescript']:
                if 'function ' in line or '=>' in line:
                    metrics['functions'] += 1
                elif 'class ' in line:
                    metrics['classes'] += 1
                elif 'import ' in line:
                    metrics['imports'] += 1
                    
        if lines:
            metrics['avg_line_length'] = total_length / len(lines)
            
        return metrics

    def render(self):
        """Renderizza il componente."""
        selected_file = st.session_state.get('selected_file')
        if selected_file and (file_info := st.session_state.files.get(selected_file)):
            st.markdown("### 🔍 Analisi File")
            
            # Statistiche di base
            line_stats = self._count_lines_by_type(file_info['content'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Linee di codice", line_stats['code'])
            with col2:
                st.metric("Commenti", line_stats['comments'])
            with col3:
                st.metric("Linee vuote", line_stats['blank'])
            
            # Analisi complessità
            st.markdown("#### Metriche di complessità")
            metrics = self._analyze_complexity(file_info['content'], file_info['language'])
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Funzioni", metrics['functions'])
            with col2:
                st.metric("Classi", metrics['classes'])
            with col3:
                st.metric("Import", metrics['imports'])
            
            # Metriche di leggibilità
            st.markdown("#### Leggibilità")
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Lunghezza max riga", metrics['max_line_length'])
            with col2:
                st.metric("Lunghezza media riga", f"{metrics['avg_line_length']:.1f}")
            
            if st.checkbox("Mostra distribuzione linee"):
                total_lines = sum(line_stats.values())
                st.markdown("#### Distribuzione linee")
                for category, count in line_stats.items():
                    percentage = (count / total_lines) * 100
                    st.progress(percentage / 100, 
                              text=f"{category.title()}: {count} ({percentage:.1f}%)")
        else:
            st.info("Seleziona un file per visualizzare l'analisi")