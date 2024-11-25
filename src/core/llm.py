"""
LLM integration for Allegro IO Code Assistant.
Manages interactions with OpenAI and Anthropic models with proper error handling,
rate limiting, and model-specific optimizations.
"""

from typing import Dict, Optional, Tuple, Generator, List, Any, Union, AsyncGenerator
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import functools
import asyncio
import logging
import random
import json
import time
import sys
import traceback

# Third-party imports
import streamlit as st
from openai import OpenAI
from anthropic import Anthropic
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionChunk,
    ChatCompletionMessage,
    ChatCompletionMessageParam
)
from anthropic.types import (
    Message,
    MessageParam,
    MessageStreamEvent,
    ContentBlockDelta,
    MessageStartEvent,
    ContentBlockStartEvent,
    ContentBlockStopEvent,
    MessageStopEvent
)

# Local imports
from .session import SessionManager
from ..utils.helpers import TokenCounter

# Type aliases for better code clarity
ModelName = str
TokenCount = int
Cost = float
ErrorMessage = str
CompletionResponse = Union[str, Generator[str, None, None]]

class LLMManager:
    """Gestisce le interazioni con i modelli LLM."""
    
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1  # secondi
    MAX_RETRY_DELAY = 16    # secondi
    
    def __init__(self):
        """Inizializza le connessioni API e le configurazioni."""
        self.logger = logging.getLogger(__name__)
        self.openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        self.anthropic_client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        
        # Costi per 1K tokens (in USD)
        self.cost_map = {
            'o1-preview': {'input': 0.01, 'output': 0.03},
            'o1-mini': {'input': 0.001, 'output': 0.002},
            'claude-3-5-sonnet-20241022': {'input': 0.008, 'output': 0.024}
        }
        
        # Limiti dei modelli
        self.model_limits = {
            'o1-preview': {
                'max_tokens': 32768,
                'context_window': 128000,
                'supports_files': False,
                'supports_system_message': False,
                'supports_functions': False
            },
            'o1-mini': {
                'max_tokens': 65536,
                'context_window': 128000,
                'supports_files': False,
                'supports_system_message': False,
                'supports_functions': False
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
        
        # Metriche e statistiche
        self._metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'average_latency': 0.0,
            'errors': []
        }
    
    def select_model(self, task_type: str, content_length: int, 
                    requires_file_handling: bool = False) -> str:
        """
        Seleziona automaticamente il modello più appropriato.
        
        Args:
            task_type: Tipo di task (es. 'architecture', 'review', 'debug')
            content_length: Lunghezza del contenuto in caratteri
            requires_file_handling: Se il task richiede manipolazione di file
            
        Returns:
            str: Nome del modello selezionato
        """
        # Se richiede gestione file, usa Claude
        if requires_file_handling:
            return "claude-3-5-sonnet-20241022"
        
        # Stima tokens
        estimated_tokens = TokenCounter.count_tokens(content_length)
        
        # Se supera i limiti di o1-preview, usa Claude
        if estimated_tokens > self.model_limits['o1-preview']['max_tokens']:
            return "claude-3-5-sonnet-20241022"
        
        # Per task complessi usa o1-preview
        if task_type in ["architecture", "review", "security"]:
            return "o1-preview"
        
        # Per task più semplici usa o1-mini
        return "o1-mini"

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

    async def _handle_o1_completion(self, messages: List[Dict], model: str) -> Generator[str, None, None]:
        """
        Gestisce le chiamate ai modelli o1 con streaming.
        
        Args:
            messages: Lista di messaggi per la chat
            model: Nome del modello o1
            
        Yields:
            str: Chunks della risposta
        """
        try:
            self._enforce_rate_limit(model)
            
            completion = await self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_completion_tokens=self.model_limits[model]['max_tokens']
            )
            
            async for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = f"Errore con {model}: {str(e)}"
            self._metrics['failed_requests'] += 1
            self._metrics['errors'].append({
                'model': model,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            self.logger.error(error_msg)
            st.error(error_msg)
            yield error_msg

    async def _handle_claude_completion_with_user_control(self, messages: List[Dict], 
                                                  placeholder: st.empty) -> Generator[str, None, None]:
        """
        Gestisce le chiamate a Claude con retry controllato dall'utente.
        
        Args:
            messages: Lista di messaggi per la chat
            placeholder: Streamlit placeholder per l'UI
            
        Yields:
            str: Chunks della risposta
        """
        for attempt in range(self.MAX_RETRIES):
            try:
                self._enforce_rate_limit("claude-3-5-sonnet-20241022")
                
                # Converti messaggi nel formato Claude
                claude_messages = []
                for msg in messages:
                    if msg["role"] == "user":
                        content_msg = {
                            "role": "user",
                            "content": [{"type": "text", "text": msg["content"]}]
                        }
                        claude_messages.append(content_msg)
                
                response = await self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    messages=claude_messages,
                    stream=True
                )
                
                async for chunk in response:
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
                            await asyncio.sleep(retry_delay)
                            continue
                        elif switch_o1:
                            st.info("Passaggio a O1-preview...")
                            async for chunk in self._handle_o1_completion(messages, "o1-preview"):
                                yield chunk
                            return
                        elif switch_mini:
                            st.info("Passaggio a O1-mini...")
                            async for chunk in self._handle_o1_completion(messages, "o1-mini"):
                                yield chunk
                            return
                        else:
                            st.stop()
                else:
                    self._metrics['failed_requests'] += 1
                    self._metrics['errors'].append({
                        'model': 'claude-3-5-sonnet-20241022',
                        'error': error_msg,
                        'timestamp': datetime.now().isoformat()
                    })
                    self.logger.error(f"Errore API: {error_msg}")
                    st.error(f"Errore API: {error_msg}")
                    if attempt < self.MAX_RETRIES - 1:
                        retry_delay = self._exponential_backoff(attempt)
                        st.warning(f"Nuovo tentativo tra {retry_delay:.1f} secondi...")
                        await asyncio.sleep(retry_delay)
                    else:
                        yield f"Mi dispiace, si è verificato un errore persistente: {error_msg}"

    
    async def process_model_response(self, messages: List[Dict], current_model: str, placeholder: st.empty) -> AsyncGenerator[str, None]:
        """
        Processa la risposta del modello in modo unificato.
        
        Args:
            messages: Lista dei messaggi
            current_model: Nome del modello corrente
            placeholder: Placeholder Streamlit per UI
            
        Yields:
            str: Chunks della risposta
        """
        try:
            handler = None
            if current_model.startswith('o1'):
                handler = self._handle_o1_completion(messages, current_model)
            elif current_model == "claude-3-5-sonnet-20241022":
                handler = self._handle_claude_completion_with_user_control(messages, placeholder)
            else:
                raise ValueError(f"Modello non supportato: {current_model}")
                
            # Process response chunks
            async for chunk in handler:
                if chunk and isinstance(chunk, str):
                    yield chunk.strip()
                    
        except Exception as e:
            error_msg = f"Errore durante la generazione della risposta: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            st.error(error_msg)
            yield error_msg

    async def process_request(self, prompt: str, analysis_type: Optional[str] = None,
                    file_content: Optional[str] = None, 
                    context: Optional[str] = None) -> Generator[str, None, None]:
        """
        Processa una richiesta completa con controllo utente sul retry e fallback.
        """
        # [previous token counting and content preparation code remains the same]
        
        # Placeholder per i controlli utente
        placeholder = st.empty()
        response = ""
        start_time = time.time()
        
        try:
            # Processa la risposta del modello
            async for chunk in self.process_model_response(messages, current_model, placeholder):
                if chunk:
                    response += chunk
                    yield chunk
            
            # Processa la risposta ottenuta
            if response:
                self._process_successful_response(
                    response=response,
                    initial_tokens=initial_tokens,
                    current_model=current_model,
                    start_time=start_time,
                    placeholder=placeholder
                )
                
        except Exception as e:
            self._handle_request_error(
                error=e,
                current_model=current_model,
                analysis_type=analysis_type,
                initial_tokens=initial_tokens,
                prompt=prompt,
                file_content=file_content,
                context=context,
                placeholder=placeholder
            )

    def _process_successful_response(self, response: str, initial_tokens: int,
                                current_model: str, start_time: float,
                                placeholder: st.empty):
        """
        Processa una risposta completata con successo.
        """
        response_tokens = TokenCounter.count_tokens(response)
        total_cost = self.calculate_cost(
            current_model,
            initial_tokens,
            response_tokens
        )
        
        # Aggiorna metriche di sessione
        SessionManager.update_token_count(initial_tokens + response_tokens)
        SessionManager.update_cost(total_cost)
        
        # Aggiorna metriche interne
        self._update_metrics(
            initial_tokens=initial_tokens,
            response_tokens=response_tokens,
            total_cost=total_cost,
            start_time=start_time
        )
        
        # Log delle metriche in modalità debug
        if st.session_state.get('debug_mode', False):
            self._log_debug_metrics(
                initial_tokens=initial_tokens,
                response_tokens=response_tokens,
                total_cost=total_cost,
                latency=(time.time() - start_time),
                response=response
            )

    def _handle_request_error(self, error: Exception, current_model: str,
                            analysis_type: str, initial_tokens: int,
                            prompt: str, file_content: Optional[str],
                            context: Optional[str], placeholder: st.empty):
        """
        Gestisce gli errori durante la richiesta.
        """
        error_msg = f"Si è verificato un errore: {str(error)}"
        self._metrics['failed_requests'] += 1
        self._metrics['errors'].append({
            'model': current_model,
            'error': str(error),
            'timestamp': datetime.now().isoformat(),
            'context': {
                'analysis_type': analysis_type,
                'initial_tokens': initial_tokens
            }
        })
        self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
        st.error(error_msg)
        
        # Gestisci il recovery
        with placeholder.container():
            col1, col2 = st.columns(2)
            
            if col1.button("🔄 Riprova", key=f"retry_{hash(error_msg)}"):
                return self.process_request(prompt, analysis_type, file_content, context)
            
            if col2.button("⚡ Prova con o1-mini", key=f"fallback_{hash(error_msg)}"):
                st.session_state.current_model = "o1-mini"
                return self.process_request(prompt, analysis_type, file_content, context)
        
        return error_msg

    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
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
        
        # Validate token counts
        if input_tokens < 0 or output_tokens < 0:
            self.logger.warning(f"Token count negativo rilevato: input={input_tokens}, output={output_tokens}")
            return 0.0
            
        input_cost = (input_tokens * costs['input']) / 1000
        output_cost = (output_tokens * costs['output']) / 1000
        
        return round(input_cost + output_cost, 4)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Restituisce le metriche correnti del LLMManager.
        
        Returns:
            Dict[str, Any]: Metriche e statistiche
        """
        return {
            'requests': {
                'total': self._metrics['total_requests'],
                'successful': self._metrics['successful_requests'],
                'failed': self._metrics['failed_requests'],
                'success_rate': (
                    (self._metrics['successful_requests'] / self._metrics['total_requests'] * 100)
                    if self._metrics['total_requests'] > 0 else 0
                )
            },
            'tokens': self._metrics['total_tokens'],
            'cost': self._metrics['total_cost'],
            'performance': {
                'average_latency': self._metrics['average_latency'],
                'rate_limits': {
                    model: {
                        'calls_last_minute': self._call_count.get(model, 0),
                        'last_call': datetime.fromtimestamp(
                            self._last_call_time.get(model, 0)
                        ).strftime('%Y-%m-%d %H:%M:%S')
                    }
                    for model in self.model_limits.keys()
                }
            },
            'errors': self._metrics['errors'][-10:]  # Ultimi 10 errori
        }

    def reset_metrics(self):
        """Resetta tutte le metriche interne."""
        self._metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'average_latency': 0.0,
            'errors': []
        }
        
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

    async def test_claude(self) -> Tuple[bool, str]:
        """
        Test di connessione base con Claude.
        
        Returns:
            Tuple[bool, str]: (successo, messaggio)
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
            
            response = await self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=100,
                messages=[test_message],
                stream=True
            )
            
            result = ""
            async for chunk in response:
                if hasattr(chunk, 'type') and chunk.type == 'content_block_delta':
                    if hasattr(chunk.delta, 'text'):
                        result += chunk.delta.text
            
            return True, result
            
        except Exception as e:
            error_msg = f"Errore test Claude: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg