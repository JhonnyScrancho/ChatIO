"""
Componente principale per l'interfaccia chat di Allegro.
Gestisce la visualizzazione dei messaggi, l'elaborazione delle risposte
e le statistiche dei token.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Optional, List, Any
from src.core.session import SessionManager
from src.core.llm import LLMManager
import pandas as pd

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
    """
    Gestisce l'interfaccia di chat dell'applicazione.
    Include gestione messaggi, statistiche e interazione con l'utente.
    """
    
    def __init__(self):
        """Inizializza la chat interface con le dipendenze e lo stato necessario."""
        self.session = SessionManager()
        self.llm = LLMManager()
        
        # Inizializzazione stato sessione
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'token_stats' not in st.session_state:
            st.session_state.token_stats = {'total': 0, 'cost': 0.0}
        if 'waiting_for_response' not in st.session_state:
            st.session_state.waiting_for_response = False
        if 'current_chat' not in st.session_state:
            st.session_state.current_chat = 'main'
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = {}
        if 'quick_prompts_enabled' not in st.session_state:
            st.session_state.quick_prompts_enabled = True
        if 'style_config' not in st.session_state:
            st.session_state.style_config = self._get_default_style()
        
        # Quick prompts predefiniti per diversi modelli
        self.quick_prompts = {
            'default': [
                "Analizza questo codice",
                "Trova bug potenziali",
                "Suggerisci miglioramenti",
                "Spiega il funzionamento"
            ],
            'grok-vision-beta': [
                "Descrivi questa immagine",
                "Trova testo nell'immagine",
                "Analizza i colori",
                "Identifica gli oggetti"
            ]
        }

    def _get_default_style(self) -> Dict[str, Any]:
        """Restituisce la configurazione di stile predefinita."""
        return {
            'chat_container_height': '600px',
            'message_spacing': '1rem',
            'user_message_bg': '#e6f3ff',
            'assistant_message_bg': '#f0f2f6',
            'input_height': '100px',
            'max_width': '800px'
        }

    def _init_chat(self, chat_id: str):
        """
        Inizializza una nuova chat con struttura dati predefinita.
        
        Args:
            chat_id: Identificatore univoco della chat
        """
        if chat_id not in st.session_state.chat_history:
            st.session_state.chat_history[chat_id] = {
                'messages': [],
                'created_at': datetime.now().isoformat(),
                'token_stats': {'total': 0, 'cost': 0.0},
                'metadata': {
                    'model': st.session_state.get('current_model', 'o1-mini'),
                    'user_settings': {}
                }
            }

    def _update_token_stats(self, tokens: int, cost: float):
        """
        Aggiorna le statistiche dei token sia per la chat corrente che globali.
        
        Args:
            tokens: Numero di token utilizzati
            cost: Costo della richiesta
        """
        chat_id = st.session_state.current_chat
        if chat_id in st.session_state.chat_history:
            # Aggiorna statistiche chat specifica
            st.session_state.chat_history[chat_id]['token_stats']['total'] += tokens
            st.session_state.chat_history[chat_id]['token_stats']['cost'] += cost
            
            # Aggiorna statistiche globali
            st.session_state.token_stats['total'] += tokens
            st.session_state.token_stats['cost'] += cost

    def _get_current_chat_messages(self) -> List[Dict[str, str]]:
        """
        Recupera i messaggi della chat corrente.
        
        Returns:
            Lista dei messaggi nella chat corrente
        """
        chat_id = st.session_state.current_chat
        if chat_id in st.session_state.chat_history:
            return st.session_state.chat_history[chat_id]['messages']
        return []

    def render_chat_controls(self):
        """Renderizza i controlli principali della chat."""
        st.markdown("""
            <style>
            .chat-controls {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem;
                background: var(--secondary-background-color);
                border-radius: 0.5rem;
                margin-bottom: 1rem;
            }
            </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            # Selezione chat
            chats = list(st.session_state.chat_history.keys())
            current_chat = st.selectbox(
                "Seleziona Chat",
                chats,
                index=chats.index(st.session_state.current_chat) if chats else 0,
                key="chat_selector"
            )
            if current_chat != st.session_state.current_chat:
                st.session_state.current_chat = current_chat
                st.rerun()

        with col2:
            # Nuova chat
            if st.button("➕ Nuova", help="Crea una nuova chat"):
                new_chat_id = f"chat_{len(st.session_state.chat_history) + 1}"
                self._init_chat(new_chat_id)
                st.session_state.current_chat = new_chat_id
                st.rerun()

        with col3:
            # Rinomina chat
            if st.button("✏️ Rinomina", help="Rinomina la chat corrente"):
                st.session_state.renaming_chat = True
                st.rerun()

        with col4:
            # Elimina chat
            if len(st.session_state.chat_history) > 1:
                if st.button("🗑️ Elimina", help="Elimina la chat corrente"):
                    if st.session_state.current_chat in st.session_state.chat_history:
                        del st.session_state.chat_history[st.session_state.current_chat]
                        st.session_state.current_chat = list(st.session_state.chat_history.keys())[0]
                        st.rerun()

        # Gestione rinomina chat
        if hasattr(st.session_state, 'renaming_chat') and st.session_state.renaming_chat:
            with st.form("rename_chat_form"):
                new_name = st.text_input("Nuovo nome per la chat:", 
                                       value=st.session_state.current_chat)
                col1, col2 = st.columns(2)
                with col1:
                    if st.form_submit_button("Conferma"):
                        if new_name and new_name != st.session_state.current_chat:
                            # Rinomina la chat mantenendo i dati
                            st.session_state.chat_history[new_name] = \
                                st.session_state.chat_history[st.session_state.current_chat]
                            del st.session_state.chat_history[st.session_state.current_chat]
                            st.session_state.current_chat = new_name
                            st.session_state.renaming_chat = False
                            st.rerun()
                with col2:
                    if st.form_submit_button("Annulla"):
                        st.session_state.renaming_chat = False
                        st.rerun()

    def render_token_stats(self):
        """Renderizza le statistiche dei token per la chat corrente."""
        chat_id = st.session_state.current_chat
        if chat_id in st.session_state.chat_history:
            stats = st.session_state.chat_history[chat_id]['token_stats']
            
            with st.expander("📊 Statistiche Token", expanded=False):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        "Token Chat",
                        f"{stats['total']:,}",
                        help="Token utilizzati in questa chat"
                    )
                
                with col2:
                    st.metric(
                        "Costo Chat",
                        f"${stats['cost']:.4f}",
                        help="Costo della chat corrente"
                    )
                
                with col3:
                    st.metric(
                        "Token Totali",
                        f"{st.session_state.token_stats['total']:,}",
                        help="Token utilizzati in totale"
                    )

                if len(st.session_state.chat_history) > 0:
                    st.markdown("### Storico Chat")
                    history_data = []
                    for chat_id, chat_data in st.session_state.chat_history.items():
                        history_data.append({
                            'Chat': chat_id,
                            'Token': chat_data['token_stats']['total'],
                            'Costo': f"${chat_data['token_stats']['cost']:.4f}",
                            'Creata': datetime.fromisoformat(chat_data['created_at']).strftime('%Y-%m-%d %H:%M')
                        })
                    if history_data:
                        df = pd.DataFrame(history_data)
                        st.dataframe(df, hide_index=True)

    def render_quick_prompts(self):
        """Renderizza i quick prompts come bottoni interattivi."""
        if not st.session_state.quick_prompts_enabled:
            return
            
        st.markdown("""
            <style>
            .quick-prompts {
                display: flex;
                flex-wrap: wrap;
                gap: 0.5rem;
                margin-bottom: 1rem;
            }
            .quick-prompt-button {
                padding: 0.5rem 1rem;
                border: 1px solid var(--primary-color);
                border-radius: 0.5rem;
                cursor: pointer;
            }
            .quick-prompt-button:hover {
                background: var(--primary-color-light);
            }
            </style>
        """, unsafe_allow_html=True)

        # Seleziona i prompt appropriati in base al modello
        current_model = st.session_state.get('current_model', 'default')
        prompts = self.quick_prompts.get(current_model, self.quick_prompts['default'])

        st.markdown("### 🚀 Quick Prompts")
        cols = st.columns(len(prompts))
        for col, prompt in zip(cols, prompts):
            with col:
                if st.button(prompt, key=f"quick_prompt_{prompt}",
                           help="Clicca per usare questo prompt",
                           use_container_width=True):
                    self.process_user_message(prompt)
                    st.rerun()

    def render(self):
        """Renderizza l'interfaccia chat completa."""
        # Renderizza controlli chat
        self.render_chat_controls()
        
        # Container principale per la chat
        chat_container = st.container()
        
        with chat_container:
            # Quick prompts
            self.render_quick_prompts()
            
            # Messaggi esistenti
            messages = self._get_current_chat_messages()
            for message in messages:
                with st.chat_message(message["role"]):
                    if isinstance(message["content"], str):
                        st.markdown(message["content"])
                    elif isinstance(message["content"], dict):
                        if "image" in message["content"]:
                            st.image(message["content"]["image"])
                        st.markdown(message["content"].get("text", ""))
            
            # Statistiche token
            self.render_token_stats()
            
            # Input chat
            if not st.session_state.waiting_for_response:
                if prompt := st.chat_input(
                    "Scrivi il tuo messaggio...",
                    key=f"chat_input_{st.session_state.current_chat}"
                ):
                    # Aggiungi messaggio utente
                    chat_id = st.session_state.current_chat
                    if chat_id in st.session_state.chat_history:
                        st.session_state.chat_history[chat_id]['messages'].append({
                            "role": "user",
                            "content": prompt
                        })
                        # Processa il messaggio
                        self.process_user_message(prompt)
                        st.rerun()

    def process_user_message(self, prompt: str):
        """
        Processa il messaggio utente e genera una risposta.
        
        Args:
            prompt: Il messaggio dell'utente da processare
        """
        try:
            # Imposta flag di processing
            st.session_state.waiting_for_response = True
            chat_id = st.session_state.current_chat
            
            # Container per la risposta
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                full_response = ""
                
                # Processa la risposta in streaming
                for chunk in self.llm.process_request(prompt=prompt):
                    if chunk:
                        full_response += chunk
                        # Aggiorna il placeholder con la risposta parziale
                        response_placeholder.markdown(full_response + "▌")
                
                # Risposta finale
                response_placeholder.markdown(full_response)
            
            # Aggiorna stato sessione
            if chat_id in st.session_state.chat_history:
                st.session_state.chat_history[chat_id]['messages'].append({
                    "role": "assistant",
                    "content": full_response
                })
            
            # Aggiorna statistiche token
            if hasattr(self.llm, 'last_token_count'):
                self._update_token_stats(
                    self.llm.last_token_count,
                    self.llm.last_cost
                )
            
            # Reset flag processing
            st.session_state.waiting_for_response = False
            
            # Forza rerun per aggiornare l'interfaccia
            st.rerun()
            
        except Exception as e:
            st.error(f"Errore durante l'elaborazione: {str(e)}")
            st.session_state.waiting_for_response = False

    def clear_chat_history(self, chat_id: Optional[str] = None):
        """
        Pulisce la cronologia della chat specificata.
        
        Args:
            chat_id: ID della chat da pulire. Se None, usa la chat corrente
        """
        if chat_id is None:
            chat_id = st.session_state.current_chat
        
        if chat_id in st.session_state.chat_history:
            st.session_state.chat_history[chat_id]['messages'] = []
            st.session_state.chat_history[chat_id]['token_stats'] = {
                'total': 0,
                'cost': 0.0
            }
            st.rerun()

    def export_chat_history(self, chat_id: Optional[str] = None) -> Optional[Dict]:
        """
        Esporta la cronologia della chat in formato JSON.
        
        Args:
            chat_id: ID della chat da esportare. Se None, usa la chat corrente
            
        Returns:
            Dict contenente la cronologia della chat o None se la chat non esiste
        """
        if chat_id is None:
            chat_id = st.session_state.current_chat
            
        if chat_id in st.session_state.chat_history:
            return {
                'messages': st.session_state.chat_history[chat_id]['messages'],
                'stats': st.session_state.chat_history[chat_id]['token_stats'],
                'created_at': st.session_state.chat_history[chat_id]['created_at'],
                'metadata': st.session_state.chat_history[chat_id]['metadata']
            }
        return None

    def import_chat_history(self, chat_data: Dict, chat_id: Optional[str] = None):
        """
        Importa una cronologia chat da un dizionario.
        
        Args:
            chat_data: Dizionario contenente i dati della chat
            chat_id: ID opzionale per la nuova chat. Se None, ne genera uno nuovo
        """
        if chat_id is None:
            chat_id = f"chat_imported_{len(st.session_state.chat_history) + 1}"
        
        if chat_id not in st.session_state.chat_history:
            st.session_state.chat_history[chat_id] = {
                'messages': chat_data.get('messages', []),
                'token_stats': chat_data.get('stats', {'total': 0, 'cost': 0.0}),
                'created_at': chat_data.get('created_at', datetime.now().isoformat()),
                'metadata': chat_data.get('metadata', {})
            }
            st.session_state.current_chat = chat_id
            st.rerun()

    def handle_file_upload(self, uploaded_file):
        """
        Gestisce l'upload di un file nella chat.
        
        Args:
            uploaded_file: File caricato attraverso st.file_uploader
        """
        try:
            content = uploaded_file.read().decode()
            message = {
                "role": "user",
                "content": f"Ho caricato il file {uploaded_file.name}:\n```\n{content}\n```"
            }
            
            chat_id = st.session_state.current_chat
            if chat_id in st.session_state.chat_history:
                st.session_state.chat_history[chat_id]['messages'].append(message)
                st.rerun()
                
        except Exception as e:
            st.error(f"Errore durante il caricamento del file: {str(e)}")

    def handle_image_upload(self, uploaded_image):
        """
        Gestisce l'upload di un'immagine nella chat.
        
        Args:
            uploaded_image: Immagine caricata attraverso st.file_uploader
        """
        try:
            chat_id = st.session_state.current_chat
            if chat_id in st.session_state.chat_history:
                message = {
                    "role": "user",
                    "content": {
                        "image": uploaded_image,
                        "text": f"Ho caricato l'immagine {uploaded_image.name}"
                    }
                }
                st.session_state.chat_history[chat_id]['messages'].append(message)
                st.rerun()
                
        except Exception as e:
            st.error(f"Errore durante il caricamento dell'immagine: {str(e)}")

    def toggle_quick_prompts(self, enabled: bool):
        """
        Attiva/disattiva i quick prompts.
        
        Args:
            enabled: True per attivare, False per disattivare
        """
        st.session_state.quick_prompts_enabled = enabled
        st.rerun()

    def update_style(self, style_config: Dict[str, Any]):
        """
        Aggiorna la configurazione di stile dell'interfaccia.
        
        Args:
            style_config: Dizionario con le nuove configurazioni di stile
        """
        st.session_state.style_config.update(style_config)
        st.rerun()

    def get_chat_statistics(self) -> Dict[str, Any]:
        """
        Raccoglie statistiche complete sulla chat corrente.
        
        Returns:
            Dict con statistiche dettagliate
        """
        chat_id = st.session_state.current_chat
        if chat_id not in st.session_state.chat_history:
            return {}
            
        chat_data = st.session_state.chat_history[chat_id]
        messages = chat_data['messages']
        
        return {
            'total_messages': len(messages),
            'user_messages': sum(1 for m in messages if m['role'] == 'user'),
            'assistant_messages': sum(1 for m in messages if m['role'] == 'assistant'),
            'token_stats': chat_data['token_stats'],
            'created_at': chat_data['created_at'],
            'average_response_length': sum(len(m['content']) for m in messages if m['role'] == 'assistant') / 
                                    (sum(1 for m in messages if m['role'] == 'assistant') or 1),
            'metadata': chat_data['metadata']
        }

    def render_chat_settings(self):
        """Renderizza il pannello delle impostazioni della chat."""
        with st.expander("⚙️ Impostazioni Chat", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                # Toggle quick prompts
                enabled = st.toggle(
                    "Quick Prompts",
                    value=st.session_state.quick_prompts_enabled,
                    help="Attiva/disattiva i quick prompts"
                )
                if enabled != st.session_state.quick_prompts_enabled:
                    self.toggle_quick_prompts(enabled)
            
            with col2:
                # Selezione modello
                current_model = st.selectbox(
                    "Modello",
                    ['o1-mini', 'o1-preview', 'claude-3-5-sonnet-20241022'],
                    index=['o1-mini', 'o1-preview', 'claude-3-5-sonnet-20241022'].index(
                        st.session_state.get('current_model', 'o1-mini')
                    )
                )
                if current_model != st.session_state.get('current_model'):
                    st.session_state.current_model = current_model
                    st.rerun()
            
            # Personalizzazione stile
            st.markdown("#### Personalizzazione")
            col1, col2 = st.columns(2)
            with col1:
                new_height = st.slider(
                    "Altezza Chat",
                    min_value=300,
                    max_value=1000,
                    value=int(st.session_state.style_config['chat_container_height'].replace('px', ''))
                )
                self.update_style({'chat_container_height': f"{new_height}px"})
            
            with col2:
                new_width = st.slider(
                    "Larghezza Massima",
                    min_value=400,
                    max_value=1200,
                    value=int(st.session_state.style_config['max_width'].replace('px', ''))
                )
                self.update_style({'max_width': f"{new_width}px"})

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