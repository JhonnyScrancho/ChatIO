"""
Data Analysis Manager per Allegro IO Code Assistant.
Gestisce l'analisi automatica di file JSON, CSV, PDF e dati di forum.
"""

import pandas as pd
import json
from typing import Dict, Any, List, Optional, Tuple
import streamlit as st
from pathlib import Path
import PyPDF2
import io
from datetime import datetime
from collections import defaultdict

class DataAnalysisManager:
    """Gestisce l'analisi automatica dei dati e le query."""
    
    def __init__(self):
        self.current_dataset = None
        self.analysis_cache = {}
        self.metadata = {}
        self.forum_data = None
        self.supported_formats = {
            'json': self._analyze_json,
            'csv': self._analyze_csv,
            'pdf': self._analyze_pdf
        }
    
    def detect_file_type(self, file_content: str, filename: str) -> str:
        """Determina il tipo di file e il tipo di dati contenuti."""
        ext = Path(filename).suffix.lower()[1:]
        if ext in self.supported_formats:
            return ext
        
        # Analisi euristica del contenuto
        try:
            json.loads(file_content)
            return 'json'
        except:
            if ',' in file_content and '\n' in file_content:
                return 'csv'
        return 'unknown'
    
    def initialize_forum_analysis(self, content: str, keyword: str) -> Dict[str, Any]:
        """
        Inizializza l'analisi dei dati del forum.
        
        Args:
            content: Contenuto JSON del file
            keyword: Parola chiave estratta dal nome del file
            
        Returns:
            Dict[str, Any]: Struttura dati iniziale per l'analisi
        """
        try:
            data = json.loads(content)
            self.forum_data = {
                'keyword': keyword,
                'raw_data': data,
                'analysis_ready': False,
                'initialization_time': datetime.now().isoformat(),
                'mental_map': self._create_forum_mental_map(data)
            }
            
            return self.forum_data['mental_map']
            
        except Exception as e:
            st.error(f"Errore nell'inizializzazione dell'analisi forum: {str(e)}")
            return None
    
    def _create_forum_mental_map(self, data: List[Dict]) -> Dict[str, Any]:
        """
        Crea una mappa mentale dei dati del forum.
        
        Args:
            data: Dati del forum in formato JSON
            
        Returns:
            Dict[str, Any]: Mappa mentale strutturata
        """
        mental_map = {
            'chronological_order': [],
            'user_interactions': defaultdict(list),
            'topic_clusters': defaultdict(list),
            'sentiment_timeline': [],
            'key_users': set(),
            'keyword_clusters': defaultdict(int)
        }
        
        for thread in data:
            thread_data = {
                'url': thread['url'],
                'title': thread['title'],
                'timestamp': thread['scrape_time'],
                'posts': []
            }
            
            # Analizza ogni post nel thread
            for post in thread['posts']:
                # Timeline cronologica
                mental_map['chronological_order'].append({
                    'time': post['post_time'],
                    'author': post['author'],
                    'content_preview': post['content'][:100],
                    'sentiment': post['sentiment']
                })
                
                # Interazioni tra utenti
                if 'quoted_user' in post:
                    mental_map['user_interactions'][post['author']].append(post['quoted_user'])
                
                # Sentiment nel tempo
                mental_map['sentiment_timeline'].append({
                    'time': post['post_time'],
                    'sentiment': post['sentiment']
                })
                
                # Keywords e clustering
                for keyword in post['keywords']:
                    mental_map['keyword_clusters'][keyword] += 1
                
                # Utenti chiave (basato su numero di post)
                mental_map['key_users'].add(post['author'])
                
                thread_data['posts'].append({
                    'id': post['post_id'],
                    'author': post['author'],
                    'time': post['post_time'],
                    'sentiment': post['sentiment']
                })
        
        # Ordina cronologicamente
        mental_map['chronological_order'].sort(key=lambda x: x['time'])
        
        # Converti set in lista per serializzazione JSON
        mental_map['key_users'] = list(mental_map['key_users'])
        
        return mental_map
    
    def get_forum_analysis_status(self) -> str:
        """
        Restituisce lo stato corrente dell'analisi forum.
        
        Returns:
            str: Messaggio di stato
        """
        if not self.forum_data:
            return "Nessuna analisi forum attiva"
            
        if not self.forum_data['analysis_ready']:
            return f"Ho estratto la parola chiave '{self.forum_data['keyword']}' dal file. La struttura è chiara e sono pronto a rispondere alle domande basate sui dati forniti."
            
        return "Analisi forum attiva e pronta per le query"
    
    def query_forum_data(self, query: str) -> Dict[str, Any]:
        """
        Esegue query specifiche sui dati del forum.
        
        Args:
            query: Query in linguaggio naturale
            
        Returns:
            Dict[str, Any]: Risultati dell'analisi
        """
        if not self.forum_data or not self.forum_data['analysis_ready']:
            return {"error": "Analisi forum non inizializzata o non pronta"}
            
        mental_map = self.forum_data['mental_map']
        results = {}
        
        # Analisi temporale
        if 'time' in query.lower() or 'when' in query.lower():
            results['timeline'] = {
                'first_post': mental_map['chronological_order'][0],
                'last_post': mental_map['chronological_order'][-1],
                'total_duration': self._calculate_duration(mental_map['chronological_order'])
            }
        
        # Analisi sentiment
        if 'sentiment' in query.lower() or 'feeling' in query.lower():
            results['sentiment'] = self._analyze_sentiment_trends(mental_map['sentiment_timeline'])
        
        # Analisi utenti
        if 'user' in query.lower() or 'who' in query.lower():
            results['users'] = {
                'most_active': self._find_most_active_users(mental_map['user_interactions']),
                'key_users': mental_map['key_users'][:5]  # Top 5 users
            }
        
        # Analisi keywords
        if 'topic' in query.lower() or 'keyword' in query.lower():
            results['keywords'] = {
                'top_keywords': dict(sorted(
                    mental_map['keyword_clusters'].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:10])  # Top 10 keywords
            }
        
        return results
    
    def _calculate_duration(self, timeline: List[Dict]) -> str:
        """Calcola la durata della discussione."""
        if not timeline:
            return "N/A"
        start = datetime.fromisoformat(timeline[0]['time'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(timeline[-1]['time'].replace('Z', '+00:00'))
        duration = end - start
        return f"{duration.days} giorni, {duration.seconds // 3600} ore"
    
    def _analyze_sentiment_trends(self, sentiment_data: List[Dict]) -> Dict[str, Any]:
        """Analizza i trend del sentiment."""
        if not sentiment_data:
            return {"error": "No sentiment data available"}
            
        sentiments = [s['sentiment'] for s in sentiment_data]
        return {
            'average': sum(sentiments) / len(sentiments),
            'min': min(sentiments),
            'max': max(sentiments),
            'trend': 'positive' if sentiments[-1] > sentiments[0] else 'negative'
        }
    
    def _find_most_active_users(self, interactions: Dict[str, List]) -> List[Tuple[str, int]]:
        """Trova gli utenti più attivi basandosi sulle interazioni."""
        user_activity = defaultdict(int)
        for user, interactions_list in interactions.items():
            user_activity[user] += len(interactions_list)
        
        return sorted(user_activity.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Metodi esistenti per analisi JSON/CSV/PDF standard
    def initialize_analysis(self, content: str, filename: str):
        """Avvia l'analisi automatica quando viene caricato un file supportato."""
        file_type = self.detect_file_type(content, filename)
        if file_type in self.supported_formats:
            analyzer = self.supported_formats[file_type]
            self.metadata = {
                'file_type': file_type,
                'filename': filename,
                'timestamp': pd.Timestamp.now()
            }
            return analyzer(content)
        return None
    
    def _analyze_json(self, content: str) -> Dict[str, Any]:
        """Analizza struttura e contenuto JSON."""
        try:
            data = json.loads(content)
            if isinstance(data, list):
                df = pd.json_normalize(data)
                self.current_dataset = df
                return {
                    'structure': 'array',
                    'records': len(data),
                    'fields': df.columns.tolist(),
                    'summary': df.describe().to_dict(),
                    'sample': df.head(5).to_dict('records')
                }
            else:
                return {
                    'structure': 'object',
                    'keys': list(data.keys()),
                    'nested_levels': self._get_nest_level(data),
                    'sample': data
                }
        except Exception as e:
            st.error(f"Errore nell'analisi JSON: {str(e)}")
            return None
    
    def _analyze_csv(self, content: str) -> Dict[str, Any]:
        """Analizza struttura e statistiche CSV."""
        try:
            df = pd.read_csv(io.StringIO(content))
            self.current_dataset = df
            return {
                'rows': len(df),
                'columns': df.columns.tolist(),
                'dtypes': df.dtypes.to_dict(),
                'summary': df.describe().to_dict(),
                'missing': df.isnull().sum().to_dict(),
                'sample': df.head(5).to_dict('records')
            }
        except Exception as e:
            st.error(f"Errore nell'analisi CSV: {str(e)}")
            return None
    
    def _analyze_pdf(self, content: bytes) -> Dict[str, Any]:
        """Estrae e analizza testo da PDF."""
        try:
            pdf = PyPDF2.PdfReader(io.BytesIO(content))
            text_content = []
            for page in pdf.pages:
                text_content.append(page.extract_text())
                
            full_text = "\n".join(text_content)
            return {
                'pages': len(pdf.pages),
                'text_length': len(full_text),
                'preview': full_text[:1000],
                'structure': {
                    'pages': len(pdf.pages),
                    'has_images': any(page.images for page in pdf.pages)
                }
            }
        except Exception as e:
            st.error(f"Errore nell'analisi PDF: {str(e)}")
            return None
    
    def _get_nest_level(self, obj: Any, level: int = 0) -> int:
        """Calcola il livello di nesting di un oggetto JSON."""
        if isinstance(obj, dict):
            if not obj:
                return level
            return max(self._get_nest_level(v, level + 1) for v in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return level
            return max(self._get_nest_level(item, level + 1) for item in obj)
        return level
    
    def get_analysis_summary(self) -> str:
        """Genera un sommario dell'analisi in linguaggio naturale."""
        if not self.metadata:
            return "Nessuna analisi disponibile"
            
        if st.session_state.get('forum_analysis_mode', False):
            return self.get_forum_analysis_status()
            
        file_type = self.metadata['file_type']
        if file_type == 'json':
            return self._get_json_summary()
        elif file_type == 'csv':
            return self._get_csv_summary()
        elif file_type == 'pdf':
            return self._get_pdf_summary()
        return "Tipo file non supportato"
    
    def _get_json_summary(self) -> str:
        """Genera sommario per file JSON."""
        return "Sommario JSON: implementazione esistente..."
    
    def _get_csv_summary(self) -> str:
        """Genera sommario per file CSV."""
        return "Sommario CSV: implementazione esistente..."
    
    def _get_pdf_summary(self) -> str:
        """Genera sommario per file PDF."""
        return "Sommario PDF: implementazione esistente..."
    
    def query_data(self, query: str) -> str:
        """Interpreta e risponde a query in linguaggio naturale sui dati."""
        if st.session_state.get('forum_analysis_mode', False):
            return self.query_forum_data(query)
            
        if self.current_dataset is None:
            return "Nessun dataset caricato"
            
        return f"Dataset contiene {len(self.current_dataset)} righe e {len(self.current_dataset.columns)} colonne"