"""
Data Analysis Manager per Allegro IO Code Assistant.
Gestisce l'analisi automatica di file JSON, CSV e PDF.
"""

import pandas as pd
import json
from typing import Dict, Any, List, Optional
import streamlit as st
from pathlib import Path
import PyPDF2
import io

class DataAnalysisManager:
    """Gestisce l'analisi automatica dei dati e le query."""
    
    def __init__(self):
        self.current_dataset = None
        self.analysis_cache = {}
        self.metadata = {}
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
    
    def initialize_analysis(self, file_content: str, filename: str):
        """Avvia l'analisi automatica quando viene caricato un file supportato."""
        file_type = self.detect_file_type(file_content, filename)
        if file_type in self.supported_formats:
            analyzer = self.supported_formats[file_type]
            self.metadata = {
                'file_type': file_type,
                'filename': filename,
                'timestamp': pd.Timestamp.now()
            }
            return analyzer(file_content)
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
    
    def get_analysis_summary(self) -> str:
        """Genera un sommario dell'analisi in linguaggio naturale."""
        if not self.metadata:
            return "Nessuna analisi disponibile"
            
        file_type = self.metadata['file_type']
        if file_type == 'json':
            return self._get_json_summary()
        elif file_type == 'csv':
            return self._get_csv_summary()
        elif file_type == 'pdf':
            return self._get_pdf_summary()
        return "Tipo file non supportato"
    
    def query_data(self, query: str) -> str:
        """Interpreta e risponde a query in linguaggio naturale sui dati."""
        if self.current_dataset is None:
            return "Nessun dataset caricato"
            
        # Qui implementeremo la logica per interpretare le query
        # Per ora restituiamo solo informazioni base
        return f"Dataset contiene {len(self.current_dataset)} righe e {len(self.current_dataset.columns)} colonne"