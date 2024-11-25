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
        'gpt-4-mini': {'input': 0.01, 'output': 0.03},
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
            'gpt-4-mini': {
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
            }
        }
        
        # Cache per rate limiting
        self._last_call_time = {}
        self._call_count = {}
        self._reset_time = {}

    def select_model(self, task_type: str, content_length: int, 
                requires_file_handling: bool = False) -> str:
        """
        Seleziona automaticamente il modello più appropriato.
        """
        # Stima tokens (1 token ~ 4 caratteri)
        estimated_tokens = content_length // 4
        
        # Per contenuti molto grandi, usa sempre Claude
        if estimated_tokens > 8000:  # Ridotto per rispettare i limiti di GPT-4
            return "claude-3-5-sonnet-20241022"
        
        # Mapping task -> modello preferito
        task_model_mapping = {
            # Task complessi che richiedono esperienza e profondità
            'architecture': 'gpt-4',
            'security': 'gpt-4',
            'complex_analysis': 'gpt-4',
            'system_design': 'gpt-4',
            
            # Task di media complessità
            'review': 'gpt-4-mini',
            'refactoring': 'gpt-4-mini',
            'optimization': 'gpt-4-mini',
            'analysis': 'gpt-4-mini',
            
            # Task rapidi o semplici
            'debug': 'o1-mini',
            'quick_fix': 'o1-mini',
            'formatting': 'o1-mini',
            'documentation': 'o1-mini',
            
            # Task che richiedono contesto ampio
            'project_analysis': 'claude-3-5-sonnet-20241022',
            'codebase_review': 'claude-3-5-sonnet-20241022'
        }
        
        # Se richiede gestione file di grandi dimensioni
        if requires_file_handling and estimated_tokens > 4000:
            return 'claude-3-5-sonnet-20241022'
        
        # Per task specifici, usa il mapping se il contenuto è nei limiti
        if task_type in task_model_mapping:
            preferred_model = task_model_mapping[task_type]
            if estimated_tokens <= self.model_limits[preferred_model]['max_tokens']:
                return preferred_model
        
        # Default per task sconosciuti o contenuti che superano i limiti
        if estimated_tokens > 4000:
            return 'claude-3-5-sonnet-20241022'
        return 'o1-mini'

    def _enforce_rate_limit(self, model: str):
        """
        Implementa rate limiting per le chiamate API.
        
        Args:
            model: Nome del modello
        """
        current_time = time.time()
        
        # Inizializza contatori se necessario
        if model not in self._last_call_time:
            self._last_call_time[model] = current_time
            self._call_count[model] = 0
            self._reset_time[model] = current_time + 60
        
        # Resetta contatori se necessario
        if current_time > self._reset_time[model]:
            self._call_count[model] = 0
            self._reset_time[model] = current_time + 60
        
        # Applica rate limiting
        if self._call_count[model] >= 50:  # 50 richieste al minuto
            sleep_time = self._reset_time[model] - current_time
            if sleep_time > 0:
                time.sleep(sleep_time)
            self._call_count[model] = 0
            self._reset_time[model] = time.time() + 60
        
        self._call_count[model] += 1
        self._last_call_time[model] = current_time

    def _exponential_backoff(self, attempt: int) -> float:
        """
        Calcola il tempo di attesa per il retry con jitter.
        
        Args:
            attempt: Numero del tentativo
            
        Returns:
            float: Tempo di attesa in secondi
        """
        delay = min(self.MAX_RETRY_DELAY, 
                   self.INITIAL_RETRY_DELAY * (2 ** attempt))
        jitter = random.uniform(-0.25, 0.25) * delay
        return delay + jitter

    def _handle_o1_completion(self, messages: List[Dict], model: str) -> Generator[str, None, None]:
        """
        Gestisce le chiamate ai modelli o1.
        
        Args:
            messages: Lista di messaggi
            model: Nome del modello o1
            
        Yields:
            str: Chunks della risposta
        """
        try:
            self._enforce_rate_limit(model)
            
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_completion_tokens=32768 if model == "o1-preview" else 65536
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
            
            # Calcola lunghezza stimata del contesto
            total_length = sum(len(msg.get('content', '')) for msg in messages)
            estimated_tokens = total_length // 4
            
            # Se supera i limiti, passa a Claude
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
            
            # Fallback automatico a Claude per contenuti troppo lunghi
            if "context_length_exceeded" in str(e):
                st.warning("Contenuto troppo lungo, passaggio a Claude...")
                yield from self._handle_claude_completion_with_user_control(messages, st.empty())
            else:
                yield error_msg
    
    def _handle_claude_completion_with_user_control(self, messages: List[Dict], 
                                                  placeholder: st.empty) -> Generator[str, None, None]:
        """
        Gestisce le chiamate a Claude con retry controllato dall'utente.
        
        Args:
            messages: Lista di messaggi
            placeholder: Streamlit placeholder per l'UI
            
        Yields:
            str: Chunks della risposta
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                self._enforce_rate_limit("claude-3-5-sonnet-20241022")
                
                claude_messages = []
                for msg in messages:
                    if msg["role"] == "user":
                        content_msg = {
                            "role": "user",
                            "content": [{"type": "text", "text": msg["content"]}]
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
                        elif chunk.type == 'message_start':
                            continue
                        elif chunk.type == 'content_block_start':
                            continue
                        elif chunk.type == 'content_block_stop':
                            continue
                        elif chunk.type == 'message_stop':
                            continue
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

    def test_claude(self):
        """
        Test di connessione base con Claude.
        """
        try:
            test_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Ciao, questo è un test di connessione."
                    }
                ]
            }
            
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=100,
                messages=[test_message],
                stream=True
            )
            
            result = ""
            for chunk in response:
                if hasattr(chunk, 'type') and chunk.type == 'content_block_delta':
                    if hasattr(chunk.delta, 'text'):
                        result += chunk.delta.text
            
            return True, result
            
        except Exception as e:
            return False, str(e)

    def _prepare_file_context(self, files: Dict[str, Dict]) -> str:
        """
        Prepara il contesto dei file in un formato strutturato.
        
        Args:
            files: Dizionario dei file processati
            
        Returns:
            str: Contesto formattato dei file
        """
        if not files:
            return ""
            
        context = "\n### File Context ###\n"
        for filename, file_info in files.items():
            context += f"\nFile: {filename} (language: {file_info['language']})\n"
            context += f"```{file_info['language']}\n{file_info['content']}\n```\n"
        return context

    def prepare_prompt(self, prompt: str, analysis_type: Optional[str] = None,
                    file_content: Optional[str] = None, 
                    context: Optional[str] = None,
                    model: str = "claude-3-5-sonnet-20241022") -> List[Dict]:
        """
        Prepara il prompt includendo il contesto dei file.
        """
        # Prepara il contesto dei file caricati
        file_context = ""
        if 'uploaded_files' in st.session_state:
            file_context = self._prepare_file_context(st.session_state.uploaded_files)
        
        # Prepara il contenuto principale
        main_content = prompt
        
        # Aggiungi il contesto dei file se presente
        if file_context:
            main_content = f"{file_context}\n\n{prompt}"
        
        # Aggiungi file_content specifico se fornito
        if file_content:
            main_content += f"\nSpecific file content:\n```\n{file_content}\n```"
        
        # Aggiungi contesto aggiuntivo se fornito
        if context:
            main_content += f"\nAdditional context: {context}"
        
        # Restituisce il messaggio utente con il contesto completo
        return [{
            "role": "user",
            "content": main_content
        }]

    def process_request(self, prompt: str, analysis_type: Optional[str] = None,
                   file_content: Optional[str] = None, 
                   context: Optional[str] = None) -> Generator[str, None, None]:
        """
        Processa una richiesta completa con controllo utente sul retry e fallback.
        """
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
        """
        Calcola il costo di una richiesta.
        
        Args:
            model: Nome del modello
            input_tokens: Numero di token in input
            output_tokens: Numero di token in output
            
        Returns:
            float: Costo in USD
        """
        if model not in self.cost_map:
            return 0.0
            
        costs = self.cost_map[model]
        input_cost = (input_tokens * costs['input']) / 1000
        output_cost = (output_tokens * costs['output']) / 1000
        
        return round(input_cost + output_cost, 4)
    
    def get_model_info(self, model: str) -> Dict[str, Any]:
        """
        Restituisce informazioni dettagliate su un modello.
        
        Args:
            model: Nome del modello
            
        Returns:
            Dict[str, Any]: Informazioni sul modello
        """
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