"""
Data Analysis Manager per Allegro IO Code Assistant.
Gestisce l'analisi automatica di file JSON e dati strutturati.
"""

import pandas as pd
import json
from typing import Dict, Any, List, Optional, Tuple
import streamlit as st
from datetime import datetime
from collections import defaultdict
import random

class DataAnalysisManager:
    """Gestisce l'analisi automatica dei dati e le query."""
    
    def __init__(self):
        self.current_dataset = None
        self.analysis_cache = {}
        self.metadata = {}
        
        # Dizionario per mappare parole chiave a tipi di analisi
        self.query_keywords = {
            'distribuzione': self._analyze_distribution,
            'trend': self._analyze_trends,
            'correlazione': self._analyze_correlations,
            'statistiche': self._analyze_statistics,
            'conteggio': self._count_analysis,
            'massimo': self._analyze_max,
            'minimo': self._analyze_min,
            'media': self._analyze_average,
            'somma': self._analyze_sum,
            'raggruppa': self._group_analysis,
            'filtra': self._filter_analysis
        }

        # Template per risposte in stile chat
        self.response_templates = {
            'initial_analysis': """
📊 Ho analizzato i dati JSON. Ecco cosa ho trovato:
{summary}

Puoi chiedermi:
{suggested_queries}
""",
            'query_response': """
{response_intro}

{detailed_response}

{follow_up_suggestion}
""",
            'error': "Mi dispiace, ho incontrato un problema nell'analisi: {error_message}",
            
            'distribution': "La distribuzione dei valori mostra: {details}",
            'trend': "Ho identificato i seguenti trend: {details}",
            'correlation': "Le correlazioni principali sono: {details}",
            'statistics': "Le statistiche chiave: {details}",
            'count': "Il conteggio richiesto è: {details}",
            'max': "Il valore massimo è: {details}",
            'min': "Il valore minimo è: {details}",
            'average': "La media calcolata è: {details}",
            'sum': "La somma totale è: {details}",
            'group': "I dati raggruppati mostrano: {details}",
            'filter': "I dati filtrati mostrano: {details}"
        }

    def _detect_analysis_type(self, query: str) -> str:
        """Determina il tipo di analisi richiesta dalla query."""
        query = query.lower()
        for keyword, func in self.query_keywords.items():
            if keyword in query:
                return keyword
        return 'general'

    def _format_chat_response(self, content: Dict[str, Any], response_type: str) -> str:
        """Formatta una risposta in stile conversazionale."""
        if response_type == 'initial_analysis':
            summary_points = []
            for key, value in content.items():
                if isinstance(value, (int, float, str)):
                    summary_points.append(f"- {key}: {value}")
                elif isinstance(value, list) and value:
                    summary_points.append(f"- {key}: {', '.join(str(x) for x in value[:3])}...")
                elif isinstance(value, dict):
                    # Formatta dizionari annidati
                    formatted_dict = []
                    for k, v in value.items():
                        if isinstance(v, (int, float, str)):
                            formatted_dict.append(f"{k}: {v}")
                    if formatted_dict:
                        summary_points.append(f"- {key}:\n  " + "\n  ".join(formatted_dict))
            
            suggested = self._get_suggested_queries(content)
            
            return self.response_templates['initial_analysis'].format(
                summary="\n".join(summary_points),
                suggested_queries="\n".join(f"- {q}" for q in suggested)
            )
        
        elif response_type == 'query_response':
            response_parts = []
            
            # Gestione speciale per diversi tipi di contenuto
            for key, value in content.items():
                if isinstance(value, dict):
                    if 'error' in value:
                        response_parts.append(f"⚠️ **{key}**: {value['error']}")
                    else:
                        # Formatta dizionari in modo leggibile
                        dict_content = json.dumps(value, indent=2, ensure_ascii=False)
                        response_parts.append(f"\n**{key}**:\n```json\n{dict_content}\n```")
                elif isinstance(value, list):
                    if value:
                        # Formatta liste in modo compatto
                        list_content = ", ".join(str(x) for x in value[:5])
                        if len(value) > 5:
                            list_content += f" ... e altri {len(value)-5} elementi"
                        response_parts.append(f"**{key}**: {list_content}")
                elif isinstance(value, (int, float)):
                    # Formatta numeri con separatori delle migliaia e 2 decimali
                    formatted_value = f"{value:,.2f}" if isinstance(value, float) else f"{value:,}"
                    response_parts.append(f"**{key}**: {formatted_value}")
                else:
                    response_parts.append(f"**{key}**: {value}")
            
            # Aggiungi grafici o visualizzazioni se disponibili
            if 'visualizations' in content:
                for viz in content['visualizations']:
                    response_parts.append(f"\n{viz}")
            
            return self.response_templates['query_response'].format(
                response_intro="📊 Ecco i risultati dell'analisi:",
                detailed_response="\n".join(response_parts),
                follow_up_suggestion=self._get_follow_up_suggestion(content)
            )
        
        elif response_type == 'error':
            return self.response_templates['error'].format(
                error_message=str(content.get('error', 'Errore sconosciuto'))
            )
        
        # Per altri tipi di risposta, formatta in modo generico
        return str(content)

    def _get_suggested_queries(self, analysis_content: Dict[str, Any]) -> List[str]:
        """Genera suggerimenti di query basati sul contenuto."""
        base_suggestions = [
            "Mostrami le statistiche di base",
            "Quali sono i valori più comuni?",
            "Ci sono trend interessanti?"
        ]
        
        json_type = st.session_state.get('json_type', 'unknown')
        if json_type == 'time_series':
            base_suggestions.extend([
                "Qual è il trend temporale?",
                "Ci sono pattern stagionali?",
                "Mostrami i picchi più significativi"
            ])
        elif json_type == 'entity':
            base_suggestions.extend([
                "Quali sono le proprietà più frequenti?",
                "Come sono distribuiti i valori?",
                "Ci sono correlazioni tra le proprietà?"
            ])
        
        return base_suggestions

    def _get_follow_up_suggestion(self, query_result: Dict[str, Any]) -> str:
        """Genera un suggerimento di follow-up basato sul risultato della query."""
        suggestions = [
            "💡 Vuoi approfondire qualche aspetto specifico?",
            "💡 Posso fornire più dettagli su qualsiasi punto.",
            "💡 Ci sono altri aspetti che vorresti esplorare?",
            "💡 Posso mostrarti altre visualizzazioni di questi dati.",
            "💡 Vuoi vedere come questi dati si correlano con altre variabili?"
        ]
        return random.choice(suggestions)

    def _analyze_distribution(self, data: Any) -> Dict[str, Any]:
        """Analizza la distribuzione dei valori."""
        if isinstance(data, list):
            if all(isinstance(x, (int, float)) for x in data):
                df = pd.Series(data)
                return {
                    'count': len(df),
                    'mean': df.mean(),
                    'std': df.std(),
                    'min': df.min(),
                    'max': df.max(),
                    'quartiles': df.quantile([0.25, 0.5, 0.75]).to_dict()
                }
        return {'error': 'Dati non supportati per analisi distribuzione'}

    def _analyze_trends(self, data: Any) -> Dict[str, Any]:
        """Analizza i trend nei dati."""
        if isinstance(data, list):
            try:
                df = pd.DataFrame(data)
                if 'timestamp' in df.columns:
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    return {
                        'trend': df.groupby(df['timestamp'].dt.date).mean().to_dict(),
                        'overall_direction': 'increasing' if df.iloc[-1].mean() > df.iloc[0].mean() else 'decreasing'
                    }
            except:
                pass
        return {'error': 'Dati non supportati per analisi trend'}

    def _analyze_correlations(self, data: Any) -> Dict[str, Any]:
        """Analizza le correlazioni tra i campi."""
        try:
            df = pd.DataFrame(data)
            numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr()
                return {
                    'correlation_matrix': corr_matrix.to_dict(),
                    'strongest_correlation': {
                        'fields': tuple(corr_matrix.unstack().sort_values(ascending=False).index[1]),
                        'value': corr_matrix.unstack().sort_values(ascending=False).iloc[1]
                    }
                }
        except:
            pass
        return {'error': 'Dati non supportati per analisi correlazioni'}

    def _analyze_statistics(self, data: Any) -> Dict[str, Any]:
        """Calcola statistiche di base."""
        try:
            # Estraiamo tutti i post
            all_posts = []
            for thread in data:
                all_posts.extend(thread['posts'])
            
            df = pd.DataFrame(all_posts)
            
            stats = {
                'total_threads': len(data),
                'total_posts': len(all_posts),
                'unique_authors': len(df['author'].unique()),
                'sentiment_stats': {
                    'mean': df['sentiment'].mean(),
                    'min': df['sentiment'].min(),
                    'max': df['sentiment'].max()
                },
                'content_length_stats': df['metadata'].apply(lambda x: x['content_length']).describe().to_dict(),
                'posts_per_author': df['author'].value_counts().to_dict(),
                'timeline': {
                    'first_post': df['post_time'].min(),
                    'last_post': df['post_time'].max()
                }
            }
            
            return stats
            
        except Exception as e:
            return {'error': f'Errore analisi statistiche: {str(e)}'}

    def _count_analysis(self, data: Any) -> Dict[str, Any]:
        """Esegue analisi di conteggio."""
        if isinstance(data, list):
            return {
                'total_count': len(data),
                'unique_count': len(set(str(x) for x in data))
            }
        return {'error': 'Dati non supportati per conteggio'}

    def _analyze_max(self, data: Any) -> Dict[str, Any]:
        """Trova il valore massimo."""
        if isinstance(data, list):
            if all(isinstance(x, (int, float)) for x in data):
                return {'max_value': max(data)}
        return {'error': 'Dati non supportati per analisi massimo'}

    def _analyze_min(self, data: Any) -> Dict[str, Any]:
        """Trova il valore minimo."""
        if isinstance(data, list):
            if all(isinstance(x, (int, float)) for x in data):
                return {'min_value': min(data)}
        return {'error': 'Dati non supportati per analisi minimo'}

    def _analyze_average(self, data: Any) -> Dict[str, Any]:
        """Calcola la media."""
        if isinstance(data, list):
            if all(isinstance(x, (int, float)) for x in data):
                return {'average': sum(data) / len(data)}
        return {'error': 'Dati non supportati per calcolo media'}

    def _analyze_sum(self, data: Any) -> Dict[str, Any]:
        """Calcola la somma."""
        if isinstance(data, list):
            if all(isinstance(x, (int, float)) for x in data):
                return {'sum': sum(data)}
        return {'error': 'Dati non supportati per calcolo somma'}

    def _group_analysis(self, data: Any) -> Dict[str, Any]:
        """Esegue analisi di gruppo."""
        try:
            df = pd.DataFrame(data)
            if len(df.columns) > 1:
                group_col = df.columns[0]
                value_col = df.columns[1]
                return {
                    'groupby_results': df.groupby(group_col)[value_col].agg(['mean', 'count', 'sum']).to_dict()
                }
        except:
            pass
        return {'error': 'Dati non supportati per analisi di gruppo'}

    def _filter_analysis(self, data: Any, condition: str) -> Dict[str, Any]:
        """Filtra i dati secondo una condizione."""
        try:
            df = pd.DataFrame(data)
            # Implementa logica di filtering basata sulla condition
            return {'filtered_data': df.head().to_dict()}
        except:
            pass
        return {'error': 'Dati non supportati per filtering'}

    def query_data(self, query: str) -> str:
        """Processa una query in linguaggio naturale e restituisce una risposta."""
        try:
            if not st.session_state.get('json_type'):
                return "Mi dispiace, non ho un JSON da analizzare. Carica un file JSON e attiva l'analisi."

            # Cache check
            cache_key = f"{st.session_state.current_chat}:{query}"
            if cache_key in self.analysis_cache:
                return self.analysis_cache[cache_key]

            # Detect analysis type and get data
            analysis_type = self._detect_analysis_type(query)
            data = self._get_data_for_analysis()
            
            # Execute analysis
            if analysis_type in self.query_keywords:
                result = self.query_keywords[analysis_type](data)
            else:
                result = self._analyze_statistics(data)

            # Format response
            formatted_response = self._format_chat_response(result, 'query_response')
            
            # Cache response
            self.analysis_cache[cache_key] = formatted_response
            
            # Add to history
            from src.core.session import SessionManager
            SessionManager.add_analysis_result(
                st.session_state.current_chat,
                query,
                result
            )
            
            return formatted_response

        except Exception as e:
            return self.response_templates['error'].format(error_message=str(e))

    def _get_data_for_analysis(self) -> Any:
        """Recupera i dati per l'analisi dal file JSON corrente."""
        for filename, file_info in st.session_state.uploaded_files.items():
            if filename.endswith('.json'):
                return json.loads(file_info['content'])
        return None

    def get_analysis_summary(self) -> str:
        """Genera un sommario dell'analisi iniziale."""
        if not hasattr(st.session_state, 'json_structure'):
            return "Nessuna analisi disponibile. Carica un file JSON per iniziare."
            
        structure = st.session_state.json_structure
        json_type = st.session_state.get('json_type', 'unknown')
        
        data = self._get_data_for_analysis()
        if not data:
            return "Nessun dato JSON disponibile per l'analisi."
            
        initial_analysis = {
            'Tipo di dati': json_type,
            'Struttura': 'Array di oggetti' if structure.get('is_array') else 'Oggetto singolo',
            'Campi principali': structure.get('sample_keys', structure.get('keys', [])),
            'Dimensione': structure.get('length', 'N/A')
        }
        
        # Add type-specific analysis
        if json_type == 'time_series':
            initial_analysis.update(self._analyze_trends(data))
        elif json_type == 'entity':
            initial_analysis.update(self._analyze_statistics(data))
        
        return self._format_chat_response(initial_analysis, 'initial_analysis')
    


    
    def _analyze_time_series(self, data: Any) -> Dict[str, Any]:
        """Analizza dati di serie temporali."""
        try:
            df = pd.DataFrame(data)
            time_col = next(col for col in df.columns if col in ['timestamp', 'date', 'time'])
            df[time_col] = pd.to_datetime(df[time_col])
            
            # Trova colonne numeriche per l'analisi
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
            
            analysis = {
                'timespan': {
                    'start': df[time_col].min().isoformat(),
                    'end': df[time_col].max().isoformat(),
                    'duration': str(df[time_col].max() - df[time_col].min())
                },
                'trends': {},
                'seasonality': {},
                'outliers': {}
            }
            
            for col in numeric_cols:
                # Analisi trend
                analysis['trends'][col] = {
                    'direction': 'increasing' if df[col].iloc[-1] > df[col].iloc[0] else 'decreasing',
                    'change_percent': ((df[col].iloc[-1] - df[col].iloc[0]) / df[col].iloc[0] * 100),
                    'peaks': {
                        'max': {'value': float(df[col].max()), 'timestamp': df.loc[df[col].idxmax(), time_col].isoformat()},
                        'min': {'value': float(df[col].min()), 'timestamp': df.loc[df[col].idxmin(), time_col].isoformat()}
                    }
                }
                
                # Analisi stagionalità
                if len(df) > 2:
                    df['month'] = df[time_col].dt.month
                    monthly_avg = df.groupby('month')[col].mean()
                    analysis['seasonality'][col] = {
                        'monthly_pattern': monthly_avg.to_dict(),
                        'highest_month': int(monthly_avg.idxmax()),
                        'lowest_month': int(monthly_avg.idxmin())
                    }
                
                # Rilevamento outliers con IQR
                Q1 = df[col].quantile(0.25)
                Q3 = df[col].quantile(0.75)
                IQR = Q3 - Q1
                outliers = df[(df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))]
                if not outliers.empty:
                    analysis['outliers'][col] = [{
                        'timestamp': row[time_col].isoformat(),
                        'value': float(row[col])
                    } for _, row in outliers.iterrows()]
            
            return analysis
            
        except Exception as e:
            return {'error': f'Errore analisi time series: {str(e)}'}

    def _analyze_entity_data(self, data: Any) -> Dict[str, Any]:
        """Analizza dati di entità."""
        try:
            df = pd.DataFrame(data)
            
            analysis = {
                'summary': {
                    'total_entities': len(df),
                    'unique_ids': df['id'].nunique() if 'id' in df else None,
                },
                'properties': {},
                'distributions': {},
                'patterns': {}
            }
            
            # Analisi proprietà
            if 'properties' in df:
                if isinstance(df['properties'].iloc[0], dict):
                    property_keys = set().union(*df['properties'].apply(lambda x: x.keys()))
                    analysis['properties'] = {
                        'common_keys': list(property_keys),
                        'frequency': {key: df['properties'].apply(lambda x: key in x).mean() 
                                    for key in property_keys}
                    }
            
            # Distribuzioni per campi numerici
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
            for col in numeric_cols:
                analysis['distributions'][col] = {
                    'mean': float(df[col].mean()),
                    'median': float(df[col].median()),
                    'std': float(df[col].std()),
                    'quartiles': df[col].quantile([0.25, 0.5, 0.75]).to_dict()
                }
            
            # Pattern comuni
            categorical_cols = df.select_dtypes(include=['object']).columns
            for col in categorical_cols:
                value_counts = df[col].value_counts()
                if len(value_counts) < 50:  # Solo se i valori unici non sono troppi
                    analysis['patterns'][col] = {
                        'most_common': value_counts.head(5).to_dict(),
                        'unique_values': len(value_counts)
                    }
            
            return analysis
            
        except Exception as e:
            return {'error': f'Errore analisi entity: {str(e)}'}

    def _analyze_nested_data(self, data: Any) -> Dict[str, Any]:
        """Analizza dati con struttura nidificata."""
        try:
            def analyze_level(data_level, max_depth=3, current_depth=0):
                if current_depth >= max_depth:
                    return {'truncated': 'Max depth reached'}
                
                if isinstance(data_level, list):
                    sample_size = min(len(data_level), 5)
                    return {
                        'type': 'array',
                        'length': len(data_level),
                        'sample': [analyze_level(item, max_depth, current_depth + 1) 
                                for item in data_level[:sample_size]]
                    }
                elif isinstance(data_level, dict):
                    return {
                        'type': 'object',
                        'keys': list(data_level.keys()),
                        'nested_analysis': {k: analyze_level(v, max_depth, current_depth + 1) 
                                        for k, v in data_level.items()}
                    }
                else:
                    return {'type': type(data_level).__name__, 'value': str(data_level)}
            
            analysis = {
                'structure': analyze_level(data),
                'summary': {
                    'depth': 0,
                    'total_nodes': 0,
                    'leaf_nodes': 0
                }
            }
            
            # Calcola statistiche sulla struttura
            def count_stats(data_level, depth=0):
                nonlocal analysis
                analysis['summary']['depth'] = max(analysis['summary']['depth'], depth)
                
                if isinstance(data_level, (list, dict)):
                    analysis['summary']['total_nodes'] += 1
                    if isinstance(data_level, list):
                        for item in data_level:
                            count_stats(item, depth + 1)
                    else:
                        for v in data_level.values():
                            count_stats(v, depth + 1)
                else:
                    analysis['summary']['leaf_nodes'] += 1
            
            count_stats(data)
            return analysis
            
        except Exception as e:
            return {'error': f'Errore analisi nested: {str(e)}'}

    def _analyze_metric_data(self, data: Any) -> Dict[str, Any]:
        """Analizza dati metrici."""
        try:
            df = pd.DataFrame(data)
            
            analysis = {
                'metrics': {},
                'aggregations': {},
                'correlations': {},
                'patterns': {}
            }
            
            # Analisi per ogni metrica
            value_col = next(col for col in df.columns if col in ['value', 'metric', 'measure'])
            
            if 'metric' in df or 'name' in df:
                metric_col = 'metric' if 'metric' in df else 'name'
                for metric in df[metric_col].unique():
                    metric_data = df[df[metric_col] == metric][value_col]
                    analysis['metrics'][metric] = {
                        'count': len(metric_data),
                        'mean': float(metric_data.mean()),
                        'std': float(metric_data.std()),
                        'min': float(metric_data.min()),
                        'max': float(metric_data.max()),
                        'quartiles': metric_data.quantile([0.25, 0.5, 0.75]).to_dict()
                    }
            
            # Correlazioni tra metriche
            numeric_cols = df.select_dtypes(include=['float64', 'int64']).columns
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr()
                analysis['correlations'] = corr_matrix.to_dict()
            
            return analysis
            
        except Exception as e:
            return {'error': f'Errore analisi metric: {str(e)}'}

    def _analyze_config_data(self, data: Any) -> Dict[str, Any]:
        """Analizza dati di configurazione."""
        try:
            def analyze_config(config, path=''):
                analysis = {
                    'type': type(config).__name__,
                    'nested_paths': [],
                    'leaf_values': {},
                    'validation': {}
                }
                
                if isinstance(config, dict):
                    for key, value in config.items():
                        current_path = f"{path}.{key}" if path else key
                        if isinstance(value, (dict, list)):
                            nested = analyze_config(value, current_path)
                            analysis['nested_paths'].extend(nested['nested_paths'])
                            analysis['leaf_values'].update(nested['leaf_values'])
                        else:
                            analysis['leaf_values'][current_path] = {
                                'type': type(value).__name__,
                                'value': value
                            }
                elif isinstance(config, list):
                    for i, value in enumerate(config):
                        current_path = f"{path}[{i}]"
                        if isinstance(value, (dict, list)):
                            nested = analyze_config(value, current_path)
                            analysis['nested_paths'].extend(nested['nested_paths'])
                            analysis['leaf_values'].update(nested['leaf_values'])
                        else:
                            analysis['leaf_values'][current_path] = {
                                'type': type(value).__name__,
                                'value': value
                            }
                
                # Validazione base
                analysis['validation'] = {
                    'has_required_fields': True,  # Personalizza in base alle tue necessità
                    'type_consistency': True,
                    'invalid_values': []
                }
                
                return analysis
            
            return analyze_config(data)
            
        except Exception as e:
            return {'error': f'Errore analisi config: {str(e)}'}
