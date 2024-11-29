"""
UI components for Allegro IO Code Assistant.
"""

from collections import defaultdict
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
            
        analyzer = st.session_state.data_analyzer
        
        # Mostra info sul dataset
        st.write(f"**Dataset**: {st.session_state.get('forum_keyword', '')} forum data")
        
        # Tabs per le diverse analisi
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 Timeline", 
            "👥 Users",
            "🔑 Keywords",
            "😊 Sentiment"
        ])
        
        with tab1:
            self._render_timeline_analysis()
        
        with tab2:
            self._render_user_analysis()
            
        with tab3:
            self._render_keyword_analysis()
            
        with tab4:
            self._render_sentiment_analysis()
        
        # Query section con più spazio per i risultati
        st.markdown("---")
        st.markdown("### 🔍 Data Query")
        query = st.text_input("Ask a question about the forum data...")
        if query:
            with st.spinner("Analyzing..."):
                results = analyzer.query_forum_data(query)
            self._display_query_results(results)
    
    def _render_timeline_analysis(self):
        """Renderizza l'analisi temporale con più dettagli."""
        analyzer = st.session_state.data_analyzer
        if analyzer.forum_data:
            timeline = analyzer.forum_data['mental_map']['chronological_order']
            
            # Metriche principali
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Posts", len(timeline))
            with col2:
                st.metric("Time Span", self._calculate_timespan(timeline))
            with col3:
                st.metric("Active Days", self._calculate_active_days(timeline))
            
            # Timeline interattiva
            st.markdown("#### 📅 Post Timeline")
            for post in timeline[:10]:  # Mostra i primi 10 post
                with st.expander(f"🕒 {post['time']} - {post['author']}", expanded=False):
                    st.write(post['content_preview'])
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.caption(f"Sentiment: {post['sentiment']:.2f}")
                    with col2:
                        st.caption(f"Author: {post['author']}")
    
    def _render_user_analysis(self):
        """Renderizza l'analisi degli utenti con grafici."""
        analyzer = st.session_state.data_analyzer
        if analyzer.forum_data:
            interactions = analyzer.forum_data['mental_map']['user_interactions']
            
            # Metriche utenti
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Users", len(analyzer.forum_data['mental_map']['key_users']))
            with col2:
                st.metric("Active Users", len([u for u in interactions.values() if len(u) > 0]))
            
            # Top users chart
            st.markdown("#### 👥 Most Active Users")
            top_users = self._find_most_active_users(interactions)
            
            # Usa un grafico a barre di Streamlit
            user_names = [user[0] for user in top_users[:10]]
            user_posts = [user[1] for user in top_users[:10]]
            st.bar_chart(dict(zip(user_names, user_posts)))
    
    def _render_keyword_analysis(self):
        """Renderizza l'analisi delle keywords con word cloud."""
        analyzer = st.session_state.data_analyzer
        if analyzer.forum_data:
            keywords = analyzer.forum_data['mental_map']['keyword_clusters']
            
            # Metriche keywords
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Unique Keywords", len(keywords))
            with col2:
                st.metric("Total Mentions", sum(keywords.values()))
            
            # Keywords chart
            st.markdown("#### 🔑 Top Keywords")
            top_keywords = dict(sorted(
                keywords.items(),
                key=lambda x: x[1],
                reverse=True
            )[:15])
            
            st.bar_chart(top_keywords)
    
    def _render_sentiment_analysis(self):
        """Renderizza l'analisi del sentiment con trend."""
        analyzer = st.session_state.data_analyzer
        if analyzer.forum_data:
            sentiment_data = analyzer.forum_data['mental_map']['sentiment_timeline']
            
            # Calcolo metriche sentiment
            sentiments = [s['sentiment'] for s in sentiment_data]
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0
            
            # Metriche principali
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Average Sentiment", f"{avg_sentiment:.2f}")
            with col2:
                st.metric("Highest", f"{max(sentiments):.2f}")
            with col3:
                st.metric("Lowest", f"{min(sentiments):.2f}")
            
            # Trend chart
            st.markdown("#### 😊 Sentiment Trend")
            sentiment_df = pd.DataFrame({
                'time': [s['time'] for s in sentiment_data],
                'sentiment': sentiments
            })
            st.line_chart(sentiment_df.set_index('time'))
    
    def _display_query_results(self, results):
        """Visualizza i risultati della query in modo più organizzato."""
        if "error" in results:
            st.error(results["error"])
            return
        
        st.markdown("#### 📊 Query Results")
        
        # Timeline results
        if "timeline" in results:
            with st.expander("📅 Timeline Analysis", expanded=True):
                st.write(f"Discussion duration: {results['timeline']['total_duration']}")
                st.write("First post:", results['timeline']['first_post'])
                st.write("Last post:", results['timeline']['last_post'])
        
        # Sentiment results
        if "sentiment" in results:
            with st.expander("😊 Sentiment Analysis", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Average Sentiment", f"{results['sentiment']['average']:.2f}")
                with col2:
                    st.metric("Trend", results['sentiment']['trend'])
        
        # User results
        if "users" in results:
            with st.expander("👥 User Analysis", expanded=True):
                st.write("Most active users:")
                for user, count in results['users']['most_active']:
                    st.write(f"- {user}: {count} interactions")
        
        # Keyword results
        if "keywords" in results:
            with st.expander("🔑 Keyword Analysis", expanded=True):
                st.write("Top keywords:")
                st.bar_chart(results['keywords']['top_keywords'])
    
    @staticmethod
    def _calculate_timespan(timeline):
        """Calcola il periodo temporale totale della discussione."""
        if not timeline:
            return "N/A"
        start = datetime.fromisoformat(timeline[0]['time'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(timeline[-1]['time'].replace('Z', '+00:00'))
        days = (end - start).days
        return f"{days} days"
    
    @staticmethod
    def _calculate_active_days(timeline):
        """Calcola il numero di giorni con attività."""
        if not timeline:
            return 0
        unique_days = set(
            datetime.fromisoformat(post['time'].replace('Z', '+00:00')).date()
            for post in timeline
        )
        return len(unique_days)
    
    @staticmethod
    def _find_most_active_users(interactions):
        """Trova gli utenti più attivi basandosi sulle interazioni."""
        user_activity = defaultdict(int)
        for user, interactions_list in interactions.items():
            user_activity[user] = len(interactions_list)
        
        return sorted(user_activity.items(), key=lambda x: x[1], reverse=True)

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