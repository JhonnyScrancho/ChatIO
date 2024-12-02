"""
LLM integration for Allegro IO Code Assistant.
Manages interactions with OpenAI and Anthropic models with proper error handling,
rate limiting, and model-specific optimizations.
"""

import streamlit as st
from typing import Dict, Optional, Tuple, Generator, List, Any
from openai import OpenAI
from anthropic import Anthropic
import time
from datetime import datetime
import json
import random

class LLMManager:
    """Gestisce le interazioni con i modelli LLM."""
    
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1  # secondi
    MAX_RETRY_DELAY = 16    # secondi
    
    def __init__(self):
        """Inizializza le connessioni API e le configurazioni."""
        self.openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        self.anthropic_client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        
        # Costi per 1K tokens (in USD)
        self.cost_map = {
            'gpt-4': {'input': 0.03, 'output': 0.06},
            'gpt-4o-mini': {'input': 0.01, 'output': 0.03},
            'o1-preview': {'input': 0.01, 'output': 0.03},
            'o1-mini': {'input': 0.001, 'output': 0.002},
            'claude-3-5-sonnet-20241022': {'input': 0.008, 'output': 0.024}
        }
        
        # Limiti dei modelli
        self.model_limits = {
            'o1-preview': {
                'max_tokens': 8192,
                'context_window': 8192,
                'supports_files': False,
                'supports_system_message': False,
                'supports_functions': False
            },
            'o1-mini': {
                'max_tokens': 4096,
                'context_window': 4096,
                'supports_files': False,
                'supports_system_message': False,
                'supports_functions': False
            },
            'gpt-4': {
                'max_tokens': 128000,
                'context_window': 128000,
                'supports_files': True,
                'supports_system_message': True,
                'supports_functions': True
            },
            'gpt-4o-mini': {
                'max_tokens': 128000,
                'context_window': 128000,
                'supports_files': True,
                'supports_system_message': True,
                'supports_functions': True
            },
            'claude-3-5-sonnet-20241022': {
                'max_tokens': 200000,
                'context_window': 200000,
                'supports_files': True,
                'supports_system_message': True,
                'supports_functions': True
            }
        }
        
        # Template di sistema per diversi tipi di analisi
        self.system_templates = {
            'code_review': {
                'role': "Sei un senior software engineer che esegue code review.",
                'focus': ["Qualità del codice", "Design patterns", "Potenziali problemi", 
                         "Best practices", "Suggerimenti di miglioramento"]
            },
            'architecture': {
                'role': "Sei un architetto software che analizza la struttura del codice.",
                'focus': ["Pattern architetturali", "Principi SOLID", "Scalabilità",
                         "Manutenibilità", "Accoppiamento e coesione"]
            },
            'security': {
                'role': "Sei un esperto di sicurezza che analizza il codice.",
                'focus': ["Vulnerabilità", "Best practices di sicurezza", "Rischi potenziali",
                         "OWASP Top 10", "Validazione input"]
            },
            'performance': {
                'role': "Sei un esperto di ottimizzazione delle performance.",
                'focus': ["Colli di bottiglia", "Opportunità di ottimizzazione", 
                         "Efficienza algoritmica", "Uso delle risorse"]
            },
            'json_analysis': {
                'role': "Sei un esperto analista dati specializzato nell'analisi di dati JSON.",
                'focus': ["Struttura dati", "Pattern nei dati", "Analisi statistica",
                         "Correlazioni", "Anomalie"]
            }
        }
        
        # Cache per rate limiting
        self._last_call_time = {}
        self._call_count = {}
        self._reset_time = {}

    def select_model(self, task_type: str, content_length: int, 
                    requires_file_handling: bool = False) -> str:
        """Seleziona automaticamente il modello più appropriato."""
        estimated_tokens = content_length // 4
        
        if estimated_tokens > 8000:
            return "claude-3-5-sonnet-20241022"
        
        task_model_mapping = {
            'architecture': 'gpt-4',
            'security': 'gpt-4',
            'complex_analysis': 'gpt-4',
            'system_design': 'gpt-4',
            'json_analysis': 'claude-3-5-sonnet-20241022',
            
            'review': 'gpt-4o-mini',
            'refactoring': 'gpt-4o-mini',
            'optimization': 'gpt-4o-mini',
            'analysis': 'gpt-4o-mini',
            
            'debug': 'o1-mini',
            'quick_fix': 'o1-mini',
            'formatting': 'o1-mini',
            'documentation': 'o1-mini',
            
            'project_analysis': 'claude-3-5-sonnet-20241022',
            'codebase_review': 'claude-3-5-sonnet-20241022'
        }
        
        if requires_file_handling and estimated_tokens > 4000:
            return 'claude-3-5-sonnet-20241022'
        
        if task_type in task_model_mapping:
            preferred_model = task_model_mapping[task_type]
            if estimated_tokens <= self.model_limits[preferred_model]['max_tokens']:
                return preferred_model
        
        if estimated_tokens > 4000:
            return 'claude-3-5-sonnet-20241022'
        return 'o1-mini'

    def _enforce_rate_limit(self, model: str):
        """Implementa rate limiting per le chiamate API."""
        current_time = time.time()
        
        if model not in self._last_call_time:
            self._last_call_time[model] = current_time
            self._call_count[model] = 0
            self._reset_time[model] = current_time + 60
        
        if current_time > self._reset_time[model]:
            self._call_count[model] = 0
            self._reset_time[model] = current_time + 60
        
        if self._call_count[model] >= 50:
            sleep_time = self._reset_time[model] - current_time
            if sleep_time > 0:
                time.sleep(sleep_time)
            self._call_count[model] = 0
            self._reset_time[model] = time.time() + 60
        
        self._call_count[model] += 1
        self._last_call_time[model] = current_time

    def _exponential_backoff(self, attempt: int) -> float:
        """Calcola il tempo di attesa per il retry con jitter."""
        delay = min(self.MAX_RETRY_DELAY, 
                   self.INITIAL_RETRY_DELAY * (2 ** attempt))
        jitter = random.uniform(-0.25, 0.25) * delay
        return delay + jitter

    def _prepare_json_context(self, json_type: str, structure: Dict) -> str:
        """Prepara il contesto per l'analisi JSON."""
        context = f"""
Stai analizzando un JSON di tipo: {json_type}
Struttura dei dati:
- Tipo: {'Array di oggetti' if structure.get('is_array') else 'Oggetto singolo'}
- Campi principali: {', '.join(structure.get('sample_keys', structure.get('keys', [])))}
- Dimensione: {structure.get('length', 'N/A')} elementi

Fornisci risposte in stile conversazionale, evidenziando insights rilevanti.
"""
        return context

    def _handle_json_analysis(self, query: str) -> Generator[str, None, None]:
        """Gestisce le richieste di analisi JSON."""
        try:
            json_type = st.session_state.get('json_type', 'unknown')
            structure = st.session_state.get('json_structure', {})
            
            context = self._prepare_json_context(json_type, structure)
            messages = [
                {"role": "system", "content": self.system_templates['json_analysis']['role']},
                {"role": "system", "content": context},
                {"role": "user", "content": query}
            ]
            
            return self._handle_claude_completion(messages)
            
        except Exception as e:
            yield f"Mi dispiace, ho incontrato un errore nell'analisi: {str(e)}"

    def _handle_o1_completion(self, messages: List[Dict], model: str) -> Generator[str, None, None]:
        """Gestisce le chiamate ai modelli o1."""
        try:
            self._enforce_rate_limit(model)
            
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_completion_tokens=self.model_limits[model]['max_tokens']
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = f"Errore con {model}: {str(e)}"
            st.error(error_msg)
            yield error_msg

    def _handle_gpt4_completion(self, messages: List[Dict], model: str) -> Generator[str, None, None]:
        """Gestisce le chiamate ai modelli GPT-4."""
        try:
            self._enforce_rate_limit(model)
            
            total_length = sum(len(msg.get('content', '')) for msg in messages)
            estimated_tokens = total_length // 4
            
            if estimated_tokens > self.model_limits[model]['max_tokens']:
                st.warning(f"Contenuto troppo lungo per {model}, passaggio a Claude...")
                return self._handle_claude_completion_with_user_control(messages, st.empty())
            
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=min(4096, self.model_limits[model]['max_tokens'] - estimated_tokens),
                temperature=0.7,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = f"Errore con {model}: {str(e)}"
            st.error(error_msg)
            
            if "context_length_exceeded" in str(e):
                st.warning("Contenuto troppo lungo, passaggio a Claude...")
                yield from self._handle_claude_completion_with_user_control(messages, st.empty())
            else:
                yield error_msg

    def _handle_claude_completion(self, messages: List[Dict]) -> Generator[str, None, None]:
        """Gestisce le chiamate base a Claude."""
        self._enforce_rate_limit("claude-3-5-sonnet-20241022")
        
        claude_messages = []
        for msg in messages:
            if msg["role"] == "user":
                content_msg = {
                    "role": "user",
                    "content": [{"type": "text", "text": msg["content"]}]
                }
                claude_messages.append(content_msg)
            elif msg["role"] == "system":
                content_msg = {
                    "role": "user",
                    "content": [{"type": "text", "text": f"System: {msg['content']}"}]
                }
                claude_messages.append(content_msg)
        
        response = self.anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=claude_messages,
            stream=True
        )
        
        for chunk in response:
            if hasattr(chunk, 'type'):
                if chunk.type == 'content_block_delta':
                    if hasattr(chunk.delta, 'text'):
                        yield chunk.delta.text

    def _handle_claude_completion_with_user_control(self, messages: List[Dict], 
                                                  placeholder: st.empty) -> Generator[str, None, None]:
        """Gestisce le chiamate a Claude con retry controllato dall'utente."""
        for attempt in range(self.MAX_RETRIES):
            try:
                yield from self._handle_claude_completion(messages)
                return
                
            except Exception as e:
                error_msg = str(e)
                
                if "overloaded_error" in error_msg:
                    with placeholder.container():
                        st.error("⚠️ Server Claude sovraccarico")
                        col1, col2, col3 = st.columns(3)
                        
                        retry = col1.button("🔄 Riprova", key=f"retry_{attempt}")
                        switch_o1 = col2.button("🔀 Passa a O1", key=f"switch_o1_{attempt}")
                        switch_mini = col3.button("🔄 Passa a O1-mini", key=f"switch_mini_{attempt}")
                        
                        if retry:
                            retry_delay = self._exponential_backoff(attempt)
                            st.info(f"Nuovo tentativo tra {retry_delay:.1f} secondi...")
                            time.sleep(retry_delay)
                            continue
                        elif switch_o1:
                            st.info("Passaggio a O1-preview...")
                            yield from self._handle_o1_completion(messages, "o1-preview")
                            return
                        elif switch_mini:
                            st.info("Passaggio a O1-mini...")
                            yield from self._handle_o1_completion(messages, "o1-mini")
                            return
                        else:
                            st.stop()
                else:
                    st.error(f"Errore API: {error_msg}")
                    if attempt < self.MAX_RETRIES - 1:
                        retry_delay = self._exponential_backoff(attempt)
                        st.warning(f"Nuovo tentativo tra {retry_delay:.1f} secondi...")
                        time.sleep(retry_delay)
                    else:
                        yield f"Mi dispiace, si è verificato un errore persistente: {error_msg}"

    def prepare_prompt(self, prompt: str, analysis_type: Optional[str] = None,
                      file_content: Optional[str] = None, 
                      context: Optional[str] = None,
                      model: str = "claude-3-5-sonnet-20241022") -> List[Dict]:
        """
        Prepara il prompt includendo il contesto dei file.
        """
        messages = []
        
        # Aggiungi sistema message appropriato
        if analysis_type and analysis_type in self.system_templates:
            messages.append({
                "role": "system",
                "content": self.system_templates[analysis_type]['role']
            })
        
        # Prepara il contesto
        full_context = ""
        
        # Aggiungi contesto JSON se in modalità analisi
        if st.session_state.get('json_analysis_mode', False):
            json_type = st.session_state.get('json_type', 'unknown')
            structure = st.session_state.get('json_structure', {})
            full_context += self._prepare_json_context(json_type, structure)
        
        # Aggiungi contesto dei file
        if context:
            full_context += f"\n{context}"
        
        if file_content:
            full_context += f"\nFile Content:\n```\n{file_content}\n```"
        
        # Aggiungi il contesto se presente
        if full_context:
            messages.append({
                "role": "system",
                "content": full_context
            })
        
        # Aggiungi il prompt dell'utente
        messages.append({
            "role": "user",
            "content": prompt
        })
        
        return messages

    def process_request(self, prompt: str, analysis_type: Optional[str] = None,
                       file_content: Optional[str] = None, 
                       context: Optional[str] = None) -> Generator[str, None, None]:
        """Processa una richiesta completa con controllo utente sul retry e fallback."""
        
        # Se siamo in modalità analisi JSON, usa l'handler specifico
        if st.session_state.get('json_analysis_mode', False):
            yield from self._handle_json_analysis(prompt)
            return
        
        # Altrimenti procedi con la normale elaborazione
        requires_file_handling = bool(file_content)
        
        if analysis_type and file_content:
            model = self.select_model(analysis_type, len(file_content), requires_file_handling)
        else:
            model = st.session_state.current_model
        
        messages = self.prepare_prompt(
            prompt=prompt,
            analysis_type=analysis_type,
            file_content=file_content,
            context=context,
            model=model
        )
        
        placeholder = st.empty()
        
        try:
            if model.startswith('gpt-4'):
                yield from self._handle_gpt4_completion(messages, model)
            elif model.startswith('o1'):
                yield from self._handle_o1_completion(messages, model)
            else:
                yield from self._handle_claude_completion_with_user_control(messages, placeholder)
                
        except Exception as e:
            error_msg = f"Errore generale: {str(e)}"
            st.error(error_msg)
            with placeholder.container():
                if st.button("🔄 Riprova con modello alternativo"):
                    yield from self._handle_o1_completion(messages, "o1-mini")

    def calculate_cost(self, model: str, input_tokens: int, 
                      output_tokens: int) -> float:
        """Calcola il costo di una richiesta."""
        if model not in self.cost_map:
            return 0.0
            
        costs = self.cost_map[model]
        input_cost = (input_tokens * costs['input']) / 1000
        output_cost = (output_tokens * costs['output']) / 1000
        
        return round(input_cost + output_cost, 4)
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """Restituisce informazioni dettagliate su un modello."""
        if model not in self.model_limits:
            return {}
            
        return {
            "limits": self.model_limits[model],
            "costs": self.cost_map[model],
            "current_usage": {
                "calls_last_minute": self._call_count.get(model, 0),
                "last_call": datetime.fromtimestamp(
                    self._last_call_time.get(model, 0)
                ).strftime('%Y-%m-%d %H:%M:%S')
            }
        }