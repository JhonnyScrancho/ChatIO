"""
UI components for Allegro IO Code Assistant.
"""

import streamlit as st
from datetime import datetime
import json
from src.core.session import SessionManager
from src.core.files import FileManager
from src.core.llm import LLMManager
from src.core.data_analysis import DataAnalysisManager
from typing import Dict, Any

class ForumAnalysisInterface:
    """Componente per l'analisi dei dati del forum."""
    
    def __init__(self):
        if 'data_analyzer' not in st.session_state:
            st.session_state.data_analyzer = DataAnalysisManager()
    
    def render(self):
        """Renderizza l'interfaccia di analisi forum."""
        if not st.session_state.get('is_forum_json', False):
            return
        
        # Rimuovi il container esistente e usa la pagina principale
        st.title("📊 Forum Data Analysis")
        
        # Sposta i controlli nella parte superiore della pagina principale
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Forum Data Analysis** - Keyword: `{st.session_state.get('forum_keyword', '')}`")
        with col2:
            forum_analysis = st.toggle('Activate Analysis', 
                                    key='forum_analysis_mode',
                                    help='Enable specialized forum data analysis')
        
        if forum_analysis:
            self._render_active_analysis()
    
    def _render_active_analysis(self):
        """Renderizza l'interfaccia di analisi quando attiva."""
        analyzer = st.session_state.data_analyzer
        
        # Usa colonne per organizzare il layout nella pagina principale
        col1, col2 = st.columns([2, 1])
        
        with col1:
            # Timeline Analysis
            st.subheader("📈 Timeline Analysis")
            self._render_timeline_analysis()
            
            # User Interactions
            st.subheader("👥 User Interactions")
            self._render_user_analysis()
        
        with col2:
            # Keywords Analysis
            st.subheader("🔑 Keywords Analysis")
            self._render_keyword_analysis()
            
            # Sentiment Analysis
            st.subheader("😊 Sentiment Analysis")
            self._render_sentiment_analysis()
        
        # Query interface in basso a tutta larghezza
        st.markdown("### 🔍 Query Data")
        query = st.text_input("Ask a question about the forum data...")
        if query:
            results = analyzer.query_forum_data(query)
            self._display_query_results(results)
    
    def _render_timeline_analysis(self):
        """Renderizza l'analisi temporale."""
        analyzer = st.session_state.data_analyzer
        if analyzer.forum_data:
            timeline = analyzer.forum_data['mental_map']['chronological_order']
            
            # Usa card per il layout
            for post in timeline[:5]:
                with st.container():
                    st.markdown(f"""
                    <div style='padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 10px;'>
                        <small>{post['time']}</small><br>
                        <strong>{post['author']}</strong><br>
                        {post['content_preview']}...
                        <br><small>Sentiment: {post['sentiment']}</small>
                    </div>
                    """, unsafe_allow_html=True)
    
    def _render_user_analysis(self):
        """Renderizza l'analisi degli utenti."""
        analyzer = st.session_state.data_analyzer
        if analyzer.forum_data:
            users = analyzer.forum_data['mental_map']['key_users']
            
            # Usa metrica per visualizzare gli utenti chiave
            cols = st.columns(len(users[:5]))
            for col, user in zip(cols, users[:5]):
                with col:
                    st.metric(label="Active User", value=user)
    
    def _render_keyword_analysis(self):
        """Renderizza l'analisi delle keywords."""
        analyzer = st.session_state.data_analyzer
        if analyzer.forum_data:
            keywords = analyzer.forum_data['mental_map']['keyword_clusters']
            
            # Visualizza keywords come tag
            st.markdown("""
            <style>
                .keyword-tag {
                    display: inline-block;
                    padding: 5px 10px;
                    margin: 2px;
                    background: #f0f2f6;
                    border-radius: 15px;
                    font-size: 0.9em;
                }
            </style>
            """, unsafe_allow_html=True)
            
            for keyword, count in sorted(keywords.items(), key=lambda x: x[1], reverse=True)[:10]:
                st.markdown(f"""
                <span class='keyword-tag'>
                    {keyword} ({count})
                </span>
                """, unsafe_allow_html=True)
    
    def _render_sentiment_analysis(self):
        """Renderizza l'analisi del sentiment."""
        analyzer = st.session_state.data_analyzer
        if analyzer.forum_data:
            sentiment_data = analyzer.forum_data['mental_map']['sentiment_timeline']
            sentiments = [s['sentiment'] for s in sentiment_data]
            
            # Usa gauge chart per il sentiment
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            st.progress(min((avg_sentiment + 1) / 2, 1.0),  # Normalizza da [-1,1] a [0,1]
                       text=f"Average Sentiment: {avg_sentiment:.2f}")
            
            # Metriche aggiuntive
            cols = st.columns(2)
            cols[0].metric("Highest", f"{max(sentiments):.2f}")
            cols[1].metric("Lowest", f"{min(sentiments):.2f}")

    def _display_query_results(self, results: Dict[str, Any]):
        """
        Visualizza i risultati di una query.
        
        Args:
            results: Risultati della query
        """
        if "error" in results:
            st.error(results["error"])
            return
            
        # Display timeline results
        if "timeline" in results:
            with st.container():
                st.subheader("📅 Timeline Analysis")
                timeline = results["timeline"]
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Discussion Duration", timeline['total_duration'])
                with cols[1]:
                    st.metric("First Post", timeline['first_post']['time'])
                with cols[2]:
                    st.metric("Last Post", timeline['last_post']['time'])
        
        # Display sentiment results
        if "sentiment" in results:
            with st.container():
                st.subheader("😊 Sentiment Analysis")
                sentiment = results["sentiment"]
                cols = st.columns(3)
                with cols[0]:
                    st.metric("Average Sentiment", f"{sentiment['average']:.2f}")
                with cols[1]:
                    st.metric("Trend", sentiment['trend'])
                with cols[2]:
                    st.metric("Range", f"{sentiment['min']:.2f} to {sentiment['max']:.2f}")
        
        # Display user results
        if "users" in results:
            with st.container():
                st.subheader("👥 User Analysis")
                users = results["users"]
                
                # Most active users
                st.markdown("#### Most Active Users")
                cols = st.columns(len(users['most_active'][:5]))
                for i, (user, count) in enumerate(users['most_active'][:5]):
                    with cols[i]:
                        st.metric(f"User {i+1}", user, f"{count} interactions")
                
                # Key users
                if users['key_users']:
                    st.markdown("#### Key Participants")
                    cols = st.columns(len(users['key_users']))
                    for i, user in enumerate(users['key_users']):
                        with cols[i]:
                            st.metric("Key User", user)
        
        # Display keyword results
        if "keywords" in results:
            with st.container():
                st.subheader("🔑 Keyword Analysis")
                keywords = results["keywords"]
                
                # Create a grid of keyword metrics
                cols = st.columns(5)  # Display top 5 keywords in a row
                for i, (keyword, count) in enumerate(list(keywords['top_keywords'].items())[:5]):
                    with cols[i]:
                        st.metric(f"Keyword {i+1}", keyword, f"{count} occurrences")
                
                # Display remaining keywords as tags
                st.markdown("#### Other Keywords")
                st.markdown("""
                <style>
                    .keyword-tag {
                        display: inline-block;
                        padding: 5px 10px;
                        margin: 2px;
                        background: #f0f2f6;
                        border-radius: 15px;
                        font-size: 0.9em;
                    }
                </style>
                """, unsafe_allow_html=True)
                
                for keyword, count in list(keywords['top_keywords'].items())[5:]:
                    st.markdown(f"""
                    <span class='keyword-tag'>
                        {keyword} ({count})
                    </span>
                    """, unsafe_allow_html=True)        

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
                                except Exception as e:
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
                        st.write(f"Processed file: {file.name}")

                        # Special handling for JSON files
                        if file.name.endswith('.json'):
                            st.write(f"Analyzing JSON file: {file.name}")
                            try:
                                data = json.loads(content)
                                if isinstance(data, list) and len(data) > 0:
                                    # Check if it's a forum JSON
                                    if all(field in data[0] for field in ['url', 'title', 'posts']):
                                        st.session_state.is_forum_json = True
                                        st.session_state.forum_keyword = file.name.replace('_scraped_data.json', '')
                                        st.session_state.forum_analysis_mode = True
                            except json.JSONDecodeError as e:
                                st.write(f"Error parsing JSON: {str(e)}")

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

        # Render forum analysis interface if applicable
        if st.session_state.get('is_forum_json', False):
            forum_analysis = ForumAnalysisInterface()
            forum_analysis.render()

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
        """
        Processa un nuovo messaggio utente e renderizza correttamente le risposte.
        """
        if not prompt.strip():
            return

        # Aggiungi il messaggio utente
        st.session_state.chats[st.session_state.current_chat]['messages'].append({
            "role": "user",
            "content": prompt
        })

        # Container per la risposta in tempo reale
        response_container = st.empty()
        
        # Processa la risposta
        response = ""
        with st.spinner("Elaborazione in corso..."):
            for chunk in self.llm.process_request(prompt=prompt):
                if chunk:
                    response += chunk
                    # Aggiorna la risposta in tempo reale nel container appropriato
                    with response_container:
                        with st.chat_message("assistant"):
                            st.markdown(response)

        # Se abbiamo una risposta valida, la aggiungiamo alla chat
        if response.strip():
            st.session_state.chats[st.session_state.current_chat]['messages'].append({
                "role": "assistant",
                "content": response
            })


    def render(self):
        """
        Renderizza l'interfaccia chat con il corretto stile dei messaggi.
        """
        self.render_chat_controls()
        
        # Container per i messaggi
        messages_container = st.container()
        
        # Set per tenere traccia dei messaggi già renderizzati
        rendered_messages = set()
        
        with messages_container:
            # Renderizza tutti i messaggi nella chat corrente
            for message in st.session_state.chats[st.session_state.current_chat]['messages']:
                # Crea un hash univoco per il messaggio
                message_hash = hash(f"{message['role']}:{message['content']}")
                
                # Renderizza solo se non è già stato mostrato
                if message_hash not in rendered_messages:
                    with st.chat_message(message["role"]):
                        st.markdown(message["content"])
                    rendered_messages.add(message_hash)

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
            'gpt-4': '🧠 GPT-4 (Expert)',
            'gpt-4o-mini': '⚡ GPT-4 Mini (Fast)',
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

class DataAnalysisInterface:
    """Interfaccia per l'analisi dei dati."""
    
    def __init__(self):
        if 'data_analyzer' not in st.session_state:
            st.session_state.data_analyzer = DataAnalysisManager()
    
    def render(self):
        """Renderizza l'interfaccia di analisi dati."""
        if not st.session_state.get('analysis_mode'):
            return
            
        st.markdown("### 📊 Analisi Dati")
        
        # Mostra sommario
        with st.expander("📝 Sommario Analisi", expanded=True):
            summary = st.session_state.data_analyzer.get_analysis_summary()
            st.markdown(summary)
        
        # Input per query
        query = st.text_input("🔍 Fai una domanda sui tuoi dati...")
        if query:
            response = st.session_state.data_analyzer.query_data(query)
            st.markdown(response)
        
        # Visualizzazioni base
        if hasattr(st.session_state.data_analyzer, 'current_dataset'):
            df = st.session_state.data_analyzer.current_dataset
            if df is not None:
                st.dataframe(df.head())
                
                # Grafici base se ci sono dati numerici
                numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
                if len(numeric_cols) > 0:
                    st.line_chart(df[numeric_cols])            