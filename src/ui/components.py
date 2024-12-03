"""
UI components for Allegro IO Code Assistant.
"""

import streamlit as st
import pandas as pd
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
                        "content": "Ciao! Carica dei file o delle immagini e fammi delle domande su di essi. Posso aiutarti ad analizzarli."
                    }],
                    'created_at': datetime.now().isoformat()
                }
            }
            st.session_state.current_chat = 'Chat principale'
            
        # Quick prompts predefiniti per ogni tipo di modello
        self.quick_prompts = {
            'default': [
                "Analizza questo codice",
                "Trova potenziali bug",
                "Suggerisci miglioramenti",
                "Spiega il funzionamento"
            ],
            'grok-vision-beta': [
                "Descrivi questa immagine",
                "Trova testo nell'immagine",
                "Analizza i colori",
                "Identifica gli oggetti",
                "Analizza la composizione"
            ]
        }

    def render_quick_prompts(self):
        """Renderizza i quick prompts come bottoni."""
        st.markdown("""
            <style>
            .quick-prompts-container {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-bottom: 1rem;
                padding: 0.5rem;
                border-radius: 5px;
                background-color: #f8f9fa;
            }
            </style>
        """, unsafe_allow_html=True)

        # Seleziona i prompt appropriati in base al modello
        current_model = st.session_state.current_model
        prompts = self.quick_prompts.get(
            current_model, 
            self.quick_prompts['default']
        )

        # Container per i quick prompts
        st.markdown('<div class="quick-prompts-container">', unsafe_allow_html=True)
        cols = st.columns(len(prompts))
        for col, prompt in zip(cols, prompts):
            with col:
                if st.button(
                    prompt, 
                    key=f"quick_prompt_{prompt}", 
                    use_container_width=True
                ):
                    # Invece di processare direttamente, settiamo un flag nella session_state
                    st.session_state.quick_prompt_selected = prompt
                    st.session_state.process_quick_prompt = True
        st.markdown('</div>', unsafe_allow_html=True)

    def render_token_stats(self):
        """Renderizza le statistiche dei token per ogni messaggio."""
        
        if 'message_stats' not in st.session_state:
            st.session_state.message_stats = []
        
        with st.expander("📊 Token Usage Statistics", expanded=False):
            # Mostra statistiche per l'ultima chiamata
            if st.session_state.message_stats:
                last_call = st.session_state.message_stats[-1]
                
                cols = st.columns(4)
                with cols[0]:
                    st.metric("Input Tokens", last_call.get('input_tokens', 0))
                with cols[1]:
                    st.metric("Output Tokens", last_call.get('output_tokens', 0))
                with cols[2]:
                    st.metric("Total Tokens", last_call.get('total_tokens', 0))
                with cols[3]:
                    st.metric("Cost ($)", f"${last_call.get('cost', 0):.4f}")
                    
            # Mostra storico in una tabella
            if len(st.session_state.message_stats) > 1:
                st.markdown("### History")
                df = pd.DataFrame(st.session_state.message_stats)
                st.dataframe(df)
    
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
    
    def render(self):
        """Renderizza l'interfaccia chat."""
        self.render_chat_controls()
        self.render_token_stats()
        
        # Gestione immagini per Grok Vision
        if st.session_state.current_model == 'grok-vision-beta':
            col1, col2 = st.columns([3, 1])
            with col1:
                uploaded_image = st.file_uploader(
                    "Carica un'immagine da analizzare",
                    type=['png', 'jpg', 'jpeg', 'gif'],
                    key="image_uploader"
                )
            with col2:
                if uploaded_image:
                    st.image(uploaded_image, caption="Immagine caricata", use_column_width=True)
            
            if uploaded_image:
                st.session_state.current_image = uploaded_image

        # Renderizza i quick prompts
        self.render_quick_prompts()
        
        # Renderizza i messaggi
        for message in st.session_state.chats[st.session_state.current_chat]['messages']:
            with st.chat_message(message["role"]):
                if isinstance(message["content"], dict) and "image" in message["content"]:
                    st.image(message["content"]["image"])
                    st.write(message["content"]["text"])
                else:
                    st.write(message["content"])

        # Input per nuovi messaggi
        if prompt := st.chat_input("Scrivi un messaggio..."):
            self.process_user_message(prompt)

    def process_user_message(self, prompt: str):
        """
        Processa un messaggio utente con supporto per immagini e gestione completa degli errori.
        """
        if not prompt.strip():
            return

        # Controlla duplicazioni
        messages = st.session_state.chats[st.session_state.current_chat]['messages']
        if messages and messages[-1].get("role") == "user" and messages[-1].get("content") == prompt:
            return

        # Gestione immagine corrente se presente
        current_image = st.session_state.get('current_image')
        
        # Prepara il contenuto del messaggio
        if current_image and st.session_state.current_model == 'grok-vision-beta':
            message_content = {
                "image": current_image,
                "text": prompt
            }
        else:
            message_content = prompt

        # Aggiungi il messaggio utente alla chat
        messages.append({
            "role": "user",
            "content": message_content
        })

        try:
            # Prepara il generatore di risposta appropriato
            if current_image and st.session_state.current_model == 'grok-vision-beta':
                image_bytes = current_image.getvalue()
                response_generator = self.llm.process_image_request(image_bytes, prompt)
            else:
                # Ottieni il contesto dai file se presenti
                context = ""
                if hasattr(st.session_state, 'uploaded_files') and st.session_state.uploaded_files:
                    for filename, file_info in st.session_state.uploaded_files.items():
                        context += f"\nFile: {filename}\n```{file_info['language']}\n{file_info['content']}\n```\n"
                
                response_generator = self.llm.process_request(
                    prompt=prompt,
                    context=context
                )

            # Accumula la risposta completa
            response = ""
            with st.spinner("Elaborazione in corso..."):
                for chunk in response_generator:
                    if chunk:
                        response += chunk
                        
            # Aggiungi la risposta completa alla chat solo se non è vuota
            if response.strip():
                messages.append({
                    "role": "assistant",
                    "content": response
                })
                
            # Aggiorna le statistiche dei token se disponibili
            if hasattr(self.llm, 'update_message_stats'):
                self.llm.update_message_stats(
                    model=st.session_state.current_model,
                    input_tokens=len(prompt) // 4,
                    output_tokens=len(response) // 4,
                    cost=0.0
                )
                
            st.rerun()

        except Exception as e:
            error_msg = f"Si è verificato un errore durante l'elaborazione: {str(e)}"
            st.error(error_msg)
            
            messages.append({
                "role": "assistant",
                "content": f"🚨 {error_msg}"
            })
            
            if st.session_state.config.get('DEBUG', False):
                st.exception(e)
            st.rerun()

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

    def render_chat_controls(self):
        """
        Renderizza i controlli della chat.
        """
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            current_chat = st.selectbox(
                " ",
                options=list(st.session_state.chats.keys()),
                index=list(st.session_state.chats.keys()).index(st.session_state.current_chat),
                label_visibility="collapsed"
            )
            if current_chat != st.session_state.current_chat:
                st.session_state.current_chat = current_chat
        
        with col2:
            if st.button("🆕", help="Nuova chat"):
                new_chat_name = f"Chat {len(st.session_state.chats) + 1}"
                st.session_state.chats[new_chat_name] = {
                    'messages': [],
                    'created_at': datetime.now().isoformat()
                }
                st.session_state.current_chat = new_chat_name
        
        with col3:
            if st.button("✏️", help="Rinomina chat"):
                st.session_state.renaming = True
        
        with col4:
            if len(st.session_state.chats) > 1 and st.button("🗑️", help="Elimina chat"):
                del st.session_state.chats[st.session_state.current_chat]
                st.session_state.current_chat = list(st.session_state.chats.keys())[0]

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
            'claude-3-5-sonnet-20241022': '🎭 Claude 3.5 Sonnet (Detailed)',
            'grok-beta': '🤖 Grok Beta (Smart)',
            'grok-vision-beta': '👁️ Grok Vision (Image Analysis)'
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
            
        # Mostra info aggiuntive per Grok Vision
        if selected == 'grok-vision-beta':
            st.info("💡 Grok Vision può analizzare immagini.")

class StatsDisplay:
    """Componente per la visualizzazione delle statistiche."""
    
    def __init__(self):
        self.session = SessionManager()
    
    def render(self):
        """Renderizza il componente."""
        stats = self.session.get_api_stats()
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Tokens Used",
                f"{stats['tokens']:,}",
                delta=None
            )
        
        with col2:
            st.metric(
                "Cost ($)",
                f"${stats['cost']:.3f}",
                delta=None
            )