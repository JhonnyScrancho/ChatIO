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
        """Inizializza l'interfaccia chat."""
        self.session = SessionManager()
        self.llm = LLMManager()
        
        # Inizializza la chat se necessario
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
        
    

    def process_user_message(self, prompt: str):
        """Processa un messaggio utente."""
        if not prompt.strip():
            return

        # Aggiungi il messaggio utente
        st.session_state.chats[st.session_state.current_chat]['messages'].append({
            "role": "user",
            "content": prompt
        })

        # Processa la risposta
        response = ""
        message_placeholder = st.empty()
        
        for chunk in self.llm.process_request(prompt=prompt):
            if chunk:
                response += chunk
                with message_placeholder.container():
                    with st.chat_message("assistant"):
                        st.markdown(response)
                # Aggiorna le metriche una sola volta per chunk
                StatsDisplay.update_metrics()

        # Aggiungi la risposta completa alla chat
        if response.strip():
            st.session_state.chats[st.session_state.current_chat]['messages'].append({
                "role": "assistant",
                "content": response
            })

    def render(self):
        """Renderizza l'interfaccia chat completa."""
        # Renderizza i controlli della chat
        self.render_chat_controls()
        
        # Renderizza i messaggi non duplicati
        messages = st.session_state.chats[st.session_state.current_chat]['messages']
        for idx, message in enumerate(messages):
            # Crea un hash unico per ogni messaggio
            message_hash = hash(f"{idx}:{message['role']}:{message['content']}")
            
            # Renderizza solo se non è già stato mostrato
            if message_hash not in st.session_state.rendered_messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                st.session_state.rendered_messages.add(message_hash)

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
        """Renderizza i controlli della chat."""
        cols = st.columns([3, 1, 1, 1])
        
        # Selezione chat
        current_chat = cols[0].selectbox(
            "Seleziona chat",
            options=list(st.session_state.chats.keys()),
            index=list(st.session_state.chats.keys()).index(st.session_state.current_chat),
            label_visibility="collapsed"
        )
        
        # Nuova chat
        if cols[1].button("🆕", help="Nuova chat"):
            new_chat_name = f"Chat {len(st.session_state.chats) + 1}"
            st.session_state.chats[new_chat_name] = {
                'messages': [],
                'created_at': datetime.now().isoformat()
            }
            st.session_state.current_chat = new_chat_name
            st.rerun()
        
        # Rinomina chat
        if cols[2].button("✏️", help="Rinomina chat"):
            st.session_state.renaming = True
        
        # Elimina chat
        if len(st.session_state.chats) > 1 and cols[3].button("🗑️", help="Elimina chat"):
            del st.session_state.chats[st.session_state.current_chat]
            st.session_state.current_chat = list(st.session_state.chats.keys())[0]
            st.rerun()

        if current_chat != st.session_state.current_chat:
            st.session_state.current_chat = current_chat
            st.rerun()

    def process_message(self, prompt: str):
        """
        Processa un nuovo messaggio.
        """
        if not prompt.strip():
            return

        # Aggiungi messaggio utente
        st.session_state.chats[st.session_state.current_chat]['messages'].append({
            "role": "user",
            "content": prompt
        })

        # Processa risposta
        response = ""
        with st.chat_message("assistant"):
            placeholder = st.empty()
            for chunk in self.llm.process_request(prompt=prompt):
                if chunk:
                    response += chunk
                    placeholder.markdown(response)

        # Salva risposta completa
        if response.strip():
            st.session_state.chats[st.session_state.current_chat]['messages'].append({
                "role": "assistant",
                "content": response
            }) 

    def render(self):
        """Renderizza l'interfaccia chat."""
        # Controlli chat
        self.render_chat_controls()
        
        # Messaggi chat
        for message in st.session_state.chats[st.session_state.current_chat]['messages']:
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
            " ",  # Spazio vuoto invece di "Select Model"
            list(models.keys()),
            format_func=lambda x: models[x],
            index=list(models.keys()).index(current_model),
            label_visibility="collapsed"  # Nasconde il label
        )
        
        if selected != current_model:
            self.session.set_current_model(selected)

class StatsDisplay:
    """Componente per visualizzazione statistiche e metriche."""

    @staticmethod
    def _format_number(num: float, decimals: int = 4) -> str:
        """Formatta un numero in modo leggibile."""
        if abs(num) >= 1_000_000:
            return f"{num/1_000_000:.1f}M"
        elif abs(num) >= 1_000:
            return f"{num/1_000:.1f}K"
        else:
            return f"{num:,.{decimals}f}"

    @staticmethod
    def _get_metrics_history() -> Dict[str, list]:
        """Recupera o inizializza la cronologia delle metriche."""
        if 'metrics_history' not in st.session_state:
            st.session_state.metrics_history = {
                'tokens': [],
                'costs': [],
                'timestamps': []
            }
        return st.session_state.metrics_history

    @staticmethod
    def _calculate_delta(current: float, history: list) -> Optional[float]:
        """Calcola il delta rispetto al valore precedente."""
        if not history:
            return None
        previous = history[-1]
        return current - previous if previous != 0 else None

    @staticmethod
    def _update_history(tokens: int, cost: float):
        """Aggiorna la cronologia delle metriche."""
        history = StatsDisplay._get_metrics_history()
        history['tokens'].append(tokens)
        history['costs'].append(cost)
        history['timestamps'].append(datetime.now())
        
        # Mantieni solo le ultime 100 misurazioni
        if len(history['tokens']) > 100:
            history['tokens'] = history['tokens'][-100:]
            history['costs'] = history['costs'][-100:]
            history['timestamps'] = history['timestamps'][-100:]

    @staticmethod
    def render():
        """Renderizza il display delle statistiche."""
        # Recupera i valori correnti
        current_tokens = st.session_state.get('token_count', 0)
        current_cost = st.session_state.get('cost', 0.0)
        
        # Aggiorna la cronologia
        StatsDisplay._update_history(current_tokens, current_cost)
        history = StatsDisplay._get_metrics_history()
        
        # Calcola i delta
        token_delta = StatsDisplay._calculate_delta(current_tokens, history['tokens'])
        cost_delta = StatsDisplay._calculate_delta(current_cost, history['costs'])

        # Layout principale
        st.markdown("### 📊 Statistiche")
        
        # Prima riga: Metriche principali
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric(
                "Token Utilizzati",
                StatsDisplay._format_number(current_tokens, decimals=0),
                delta=StatsDisplay._format_number(token_delta, decimals=0) if token_delta else None,
                delta_color="off",
                help="Numero totale di token utilizzati nella sessione"
            )
            
        with col2:
            st.metric(
                "Costo Totale ($)",
                StatsDisplay._format_number(current_cost),
                delta=StatsDisplay._format_number(cost_delta) if cost_delta else None,
                delta_color="off",
                help="Costo totale della sessione in USD"
            )
        
        # Seconda riga: Metriche avanzate (espandibili)
        with st.expander("🔍 Metriche Dettagliate", expanded=False):
            detailed_col1, detailed_col2 = st.columns(2)
            
            with detailed_col1:
                # Media token per messaggio
                if history['tokens']:
                    avg_tokens = sum(history['tokens']) / len(history['tokens'])
                    st.metric(
                        "Media Token/Messaggio",
                        StatsDisplay._format_number(avg_tokens, decimals=0),
                        help="Media dei token utilizzati per messaggio"
                    )
                
                # Velocità token
                if len(history['timestamps']) > 1:
                    time_diff = (history['timestamps'][-1] - history['timestamps'][0]).total_seconds()
                    if time_diff > 0:
                        tokens_per_second = sum(history['tokens']) / time_diff
                        st.metric(
                            "Token/Secondo",
                            StatsDisplay._format_number(tokens_per_second, decimals=1),
                            help="Velocità media di elaborazione token"
                        )
            
            with detailed_col2:
                # Costo medio per messaggio
                if history['costs']:
                    avg_cost = sum(history['costs']) / len(history['costs'])
                    st.metric(
                        "Costo Medio/Messaggio",
                        f"${StatsDisplay._format_number(avg_cost)}",
                        help="Costo medio per messaggio"
                    )
                
                # Costo per token
                if current_tokens > 0:
                    cost_per_token = current_cost / current_tokens
                    st.metric(
                        "Costo/Token",
                        f"${StatsDisplay._format_number(cost_per_token * 1000)} per 1K token",
                        help="Costo medio per 1000 token"
                    )
        
        # Aggiungi pulsante di reset se necessario
        if current_tokens > 0 or current_cost > 0:
            if st.button("🔄 Reset Statistiche"):
                st.session_state.token_count = 0
                st.session_state.cost = 0.0
                st.session_state.metrics_history = {
                    'tokens': [],
                    'costs': [],
                    'timestamps': []
                }
                st.rerun()

    @staticmethod
    def update():
        """
        Aggiorna le statistiche senza ricostruire l'interfaccia.
        Da chiamare quando si vogliono aggiornare solo i valori.
        """
        StatsDisplay._update_history(
            st.session_state.get('token_count', 0),
            st.session_state.get('cost', 0.0)
        )