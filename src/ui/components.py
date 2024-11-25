"""
UI components for Allegro IO Code Assistant.
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
from src.core.session import SessionManager
from src.core.files import FileManager
from src.core.llm import LLMManager

class FileExplorer:
    """Component per l'esplorazione e l'upload dei file."""
    
    def __init__(self):
        """Inizializza il FileExplorer."""
        self.session = SessionManager()
        self.file_manager = FileManager()
        if 'uploaded_files' not in st.session_state:
            st.session_state.uploaded_files = {}

    def _get_file_icon(self, filename: str) -> str:
        """
        Restituisce l'icona appropriata per il tipo di file.
        
        Args:
            filename: Nome del file
            
        Returns:
            str: Emoji rappresentativa del tipo di file
        """
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
        Crea una struttura ad albero dai file.
        
        Args:
            files: Dizionario dei file
            
        Returns:
            Dict[str, Any]: Struttura ad albero dei file
        """
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

    def _render_tree_node(self, path: str, node: Dict[str, Any], prefix: str = "", is_last: bool = True):
        """
        Renderizza un nodo dell'albero dei file in stile minimale.
        
        Args:
            path: Percorso del nodo
            node: Contenuto del nodo
            prefix: Prefisso per l'indentazione
            is_last: Se è l'ultimo nodo del livello
        """
        PIPE = "│   "
        ELBOW = "└── "
        TEE = "├── "
        
        connector = ELBOW if is_last else TEE
        
        if isinstance(node, dict) and 'content' not in node:
            # È una directory
            st.markdown(
                f"<div style='font-family: monospace; white-space: pre;'>{prefix}{connector}{path.split('/')[-1]}/</div>",
                unsafe_allow_html=True
            )
            
            items = sorted(node.items())
            for i, (name, child) in enumerate(items):
                is_last_item = i == len(items) - 1
                new_prefix = prefix + (PIPE if not is_last else "    ")
                self._render_tree_node(name, child, new_prefix, is_last_item)
        else:
            # È un file
            file_icon = self._get_file_icon(path)
            if st.button(
                f"{prefix}{connector}{file_icon} {path.split('/')[-1]}",
                key=f"file_{path}",
                use_container_width=True,
                type="secondary"
            ):
                st.session_state.selected_file = path
                st.session_state.current_file = path

    def render(self):
        """Renderizza il componente FileExplorer."""
        uploaded_files = st.file_uploader(
            "Carica i tuoi file",
            type=['py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'md', 'txt', 'json', 'yml', 'yaml', 'zip'],
            accept_multiple_files=True
        )

        if uploaded_files:
            for file in uploaded_files:
                try:
                    if file.name.endswith('.zip'):
                        # Processa file ZIP
                        processed_files = self.file_manager.process_zip(file)
                        st.session_state.uploaded_files.update(processed_files)
                    else:
                        # Processa file singolo
                        processed = self.file_manager.process_file(file)
                        if processed:
                            st.session_state.uploaded_files[file.name] = processed

                except Exception as e:
                    st.error(f"Errore nel processare {file.name}: {str(e)}")

        # Aggiungi stili CSS per l'albero dei file
        st.markdown("""
            <style>
                .file-tree-button {
                    background: none !important;
                    border: none !important;
                    padding: 0 !important;
                    font-family: monospace !important;
                    color: inherit !important;
                    text-align: left !important;
                    width: 100% !important;
                    margin: 0 !important;
                    height: auto !important;
                    line-height: 1.5 !important;
                }
                .file-tree-button:hover {
                    color: #ff4b4b !important;
                }
                .directory-label {
                    color: #666;
                    font-family: monospace;
                }
            </style>
        """, unsafe_allow_html=True)

        # Visualizza struttura ad albero
        if st.session_state.uploaded_files:
            tree = self._create_file_tree(st.session_state.uploaded_files)
            st.markdown("<div class='directory-label'>📁 Project Files</div>", unsafe_allow_html=True)
            items = sorted(tree.items())
            for i, (name, node) in enumerate(items):
                is_last = i == len(items) - 1
                self._render_tree_node(name, node, "", is_last)

class ChatInterface:
    """Componente per l'interfaccia chat."""
    
    def __init__(self, llm_manager: Optional[LLMManager] = None):
        """
        Inizializza l'interfaccia chat.
        
        Args:
            llm_manager: Manager per le interazioni LLM
        """
        self.session = SessionManager()
        self.llm = llm_manager
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

    def _get_context(self) -> str:
        """
        Recupera il contesto dai file caricati.
        
        Returns:
            str: Contesto formattato
        """
        context = ""
        if uploaded_files := st.session_state.get('uploaded_files', {}):
            current_file = st.session_state.get('current_file')
            if current_file and current_file in uploaded_files:
                file_info = uploaded_files[current_file]
                context = f"\nFile corrente: {current_file}\n```{file_info['language']}\n{file_info['content']}\n```"
        return context

    def _process_response(self, prompt: str) -> str:
        """
        Processa la richiesta e genera una risposta.
        
        Args:
            prompt: Prompt dell'utente
            
        Returns:
            str: Risposta generata
        """
        try:
            if not self.llm:
                return "Error: LLM manager not initialized"
                
            context = self._get_context()
            response = "".join(list(self.llm.process_request(
                prompt=prompt,
                context=context
            )))
            return response
        except Exception as e:
            error_msg = f"Errore durante l'elaborazione: {str(e)}"
            st.error(error_msg)
            return error_msg

    def render(self):
        """Renderizza l'interfaccia chat."""
        # Recupera la chat corrente
        current_chat = st.session_state.chats[st.session_state.current_chat]
        
        # Container per i messaggi
        messages_container = st.container()
        
        # Renderizza i messaggi
        with messages_container:
            for message in current_chat['messages']:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
        
        # Input chat con gestione diretta
        if prompt := st.chat_input("Chiedi qualcosa sul tuo codice...", key="chat_input"):
            with st.spinner("Elaborazione in corso..."):
                response = self._process_response(prompt)
                
                # Aggiorna la chat
                current_chat['messages'].extend([
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": response}
                ])
                
                # Forza il refresh
                st.rerun()

class CodeViewer:
    """Componente per la visualizzazione del codice."""
    
    def __init__(self):
        """Inizializza il CodeViewer."""
        self.session = SessionManager()

    def render(self):
        """Renderizza il componente."""
        selected_file = st.session_state.get('selected_file')
        if selected_file and (file_info := st.session_state.uploaded_files.get(selected_file)):
            st.markdown(f"**{file_info['name']}** ({file_info['language']})")
            st.code(file_info['content'], language=file_info['language'])
            
            # Aggiungi statistiche del file
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Lines", len(file_info['content'].splitlines()))
            with col2:
                st.metric("Size", f"{len(file_info['content'])} chars")
            with col3:
                st.metric("Language", file_info['language'].upper())
        else:
            st.info("Seleziona un file dalla sidebar per visualizzarne il contenuto")

class ModelSelector:
    """Componente per la selezione del modello LLM."""
    
    def __init__(self):
        """Inizializza il ModelSelector."""
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
            "Seleziona Modello",
            list(models.keys()),
            format_func=lambda x: models[x],
            index=list(models.keys()).index(current_model)
        )
        
        if selected != current_model:
            self.session.set_current_model(selected)
            
        # Mostra info sul modello
        with st.expander("Informazioni sul modello"):
            model_info = {
                'o1-mini': {
                    'description': 'Ottimizzato per risposte veloci e debugging semplice',
                    'best_for': ['Quick fixes', 'Simple debugging', 'Small files'],
                    'response_time': 'Fast (0.5-1s)'
                },
                'o1-preview': {
                    'description': 'Bilanciato per analisi approfondita e suggerimenti avanzati',
                    'best_for': ['Code review', 'Architecture analysis', 'Performance optimization'],
                    'response_time': 'Medium (1-2s)'
                },
                'claude-3-5-sonnet': {
                    'description': 'Massima capacità di analisi e contestualizzazione',
                    'best_for': ['Complex analysis', 'Large codebases', 'Detailed explanations'],
                    'response_time': 'Slow (2-4s)'
                }
            }
            
            info = model_info[selected]
            st.markdown(f"**{info['description']}**")
            st.markdown("**Best for:**")
            for use_case in info['best_for']:
                st.markdown(f"- {use_case}")
            st.info(f"Response time: {info['response_time']}")

class StatsDisplay:
    """Componente per la visualizzazione delle statistiche."""
    
    def __init__(self):
        """Inizializza il StatsDisplay."""
        self.session = SessionManager()
    
    def render(self):
        """Renderizza il componente."""
        stats = self.session.get_stats()
        
        # Metriche principali
        col1, col2 = st.columns(2)
        with col1:
            st.metric(
                "Token Usati",
                f"{stats['token_count']:,}",
                delta=None
            )
        with col2:
            st.metric(
                "Costo ($)",
                f"${stats['cost']:.3f}",
                delta=None
            )
        
        # Statistiche aggiuntive
        with st.expander("Statistiche dettagliate"):
            st.markdown(f"""
            - **File caricati:** {stats['files_count']}
            - **Chat attive:** {stats['chats_count']}
            - **Costo medio per richiesta:** ${stats['cost'] / max(stats['token_count'] / 1000, 1):.4f}/1K tokens
            - **Sessione iniziata:** {datetime.fromisoformat(st.session_state.get('start_time', datetime.now().isoformat())).strftime('%Y-%m-%d %H:%M:%S')}
            """)