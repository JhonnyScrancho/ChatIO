"""
LLM integration for Allegro IO Code Assistant.
Manages interactions with OpenAI and Anthropic models with proper error handling,
rate limiting, and model-specific optimizations.
"""

import pandas as pd
from core.session import SessionManager
import streamlit as st
from typing import Dict, Optional, Tuple, Generator, List, Any, Union
from openai import OpenAI
from anthropic import Anthropic
import time
from datetime import datetime
import json
import random
import os
import base64
from PIL import Image
from io import BytesIO

class LLMManager:
    """Gestisce le interazioni con i modelli LLM."""
    
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1  # secondi
    MAX_RETRY_DELAY = 16    # secondi
    
    def __init__(self):
        """Inizializza le connessioni API e le configurazioni."""
        self.openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        self.anthropic_client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        self.grok_client = OpenAI(
            api_key=st.secrets["XAI_API_KEY"],
            base_url="https://api.x.ai/v1"
        )

        # Initialize session state for message stats
        if 'message_stats' not in st.session_state:
            st.session_state.message_stats = []
        
        # Initialize total_stats in session state
        if 'total_stats' not in st.session_state:
            st.session_state.total_stats = {
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'total_cost': 0.0
            }
        
        
        # Costi per 1K tokens (in USD)
        self.cost_map = {
            'o1-mini': {'input': 0.003, 'output': 0.012},         # $3.00 e $12.00 per milione
            'o1-preview': {'input': 0.015, 'output': 0.060},      # $15.00 e $60.00 per milione
            'o1-mini-2024-09-12': {'input': 0.003, 'output': 0.012},  # $3.00 e $12.00 per milione
            'o1-preview-2024-09-12': {'input': 0.015, 'output': 0.060},  # $15.00 e $60.00 per milione
            'gpt-4o-2024-08-06': {'input': 0.0025, 'output': 0.010},  # $2.50 e $10.00 per milione
            'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},  # $0.15 e $0.60 per milione
            'gpt-4o': {'input': 0.0025, 'output': 0.010},         # $2.50 e $10.00 per milione
            'gpt-4o-2024-05-13': {'input': 0.005, 'output': 0.015},  # $5.00 e $15.00 per milione
            'gpt-4-turbo-2024-04': {'input': 0.01, 'output': 0.03},  # $10.00 e $30.00 per milione
            'gpt-3.5-turbo-0125': {'input': 0.0005, 'output': 0.0015},  # $0.50 e $1.50 per milione
            'claude-3-5-sonnet-20241022': {'input': 0.003, 'output': 0.015},  # $3.00 e $15.00 per milione
            'claude-3-haiku': {'input': 0.00025, 'output': 0.00125},  # $0.25 e $1.25 per milione
            'grok-beta': {'input': 0.0006, 'output': 0.0008},     # $0.60 e $0.80 per milione
            'grok-vision-beta': {'input': 0.00024, 'output': 0.00024},  # $0.24 e $0.24 per milione
        }
        
        # Limiti dei modelli
        self.model_limits = {
            'o1-preview-2024-09-12': {
                'max_tokens': 32768,
                'context_window': 128000,
                'supports_files': False,
                'supports_system_message': True,
                'supports_functions': True
            },
            'o1-mini-2024-09-12': {
                'max_tokens': 65536,
                'context_window': 128000,
                'supports_files': False,
                'supports_system_message': True,
                'supports_functions': True
            },
            'claude-3-5-sonnet-20241022': {
                'max_tokens': 4096,
                'context_window': 200000,
                'supports_files': True,
                'supports_system_message': True,
                'supports_functions': True
            },
            'gpt-4o': {
                'max_tokens': 2048,
                'context_window': 128000,
                'supports_files': False,
                'supports_system_message': True,
                'supports_functions': True
            },
            'gpt-4o-mini': {
                'max_tokens': 16384,
                'context_window': 128000,
                'supports_files': False,
                'supports_system_message': True,
                'supports_functions': True
            },
            'grok-beta': {
                'max_tokens': 4096,
                'context_window': 8192,
                'supports_files': False,
                'supports_system_message': True,
                'supports_functions': True
            },
            'grok-vision-beta': {
                'max_tokens': 4096,
                'context_window': 8192,
                'supports_files': True,
                'supports_system_message': True,
                'supports_functions': True,
                'supports_vision': True
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
                    requires_file_handling: bool = False,
                    requires_vision: bool = False) -> str:
        """
        Seleziona automaticamente il modello più appropriato.
        
        Args:
            task_type: Tipo di task (es. 'architecture', 'review', 'debug')
            content_length: Lunghezza del contenuto in caratteri
            requires_file_handling: Se il task richiede manipolazione di file
            requires_vision: Se il task richiede analisi di immagini
            
        Returns:
            str: Nome del modello selezionato
        """
        # Se richiede analisi di immagini, usa Grok Vision
        if requires_vision:
            return "grok-vision-beta"
        
        # Se richiede gestione file complessa, usa Claude
        if requires_file_handling and content_length > 8000:
            return "claude-3-5-sonnet-20241022"
        
        # Stima tokens (1 token ~ 4 caratteri)
        estimated_tokens = content_length // 4
        
        # Per task più complessi con contesto limitato, usa Grok Beta
        if task_type in ["review", "architecture"] and estimated_tokens <= 8000:
            return "grok-beta"
        
        # Per contesti molto grandi, usa Claude
        if estimated_tokens > 32000:
            return "claude-3-5-sonnet-20241022"
        
        # Per task complessi con contesto medio, usa o1-preview
        if task_type in ["architecture", "review", "security"]:
            return "o1-preview"
        
        # Per task più semplici usa o1-mini
        return "o1-mini"
    
    def _handle_grok_completion(self, messages: List[Dict], model: str) -> Generator[str, None, None]:
        """
        Gestisce le chiamate ai modelli Grok.
        
        Args:
            messages: Lista di messaggi
            model: Nome del modello Grok
            
        Yields:
            str: Chunks della risposta
        """
        try:
            self._enforce_rate_limit(model)
            
            completion = self.grok_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=4096
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = f"Errore con {model}: {str(e)}"
            st.error(error_msg)
            yield error_msg

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

    def update_message_stats(self, model: str, input_tokens: int, output_tokens: int, cost: float):
        """Aggiorna le statistiche in modo atomico e sincronizzato."""
        if 'message_stats' not in st.session_state:
            st.session_state.message_stats = []
            st.session_state.total_stats = {
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'total_cost': 0.0
            }
        
        # Calcola il costo corretto usando i prezzi dal cost_map
        costs = self.cost_map[model]
        actual_cost = (input_tokens * costs['input'] + output_tokens * costs['output']) / 1000
        
        # Aggiunge nuova entry nella history
        new_stat = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'model': model,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens,
            'cost': actual_cost
        }
        
        st.session_state.message_stats.append(new_stat)
        
        # Aggiorna i totali
        st.session_state.total_stats['input_tokens'] += input_tokens
        st.session_state.total_stats['output_tokens'] += output_tokens
        st.session_state.total_stats['total_tokens'] += (input_tokens + output_tokens)
        st.session_state.total_stats['total_cost'] += actual_cost

    def render_token_stats(self):
        """Renderizza le statistiche in modo sincronizzato."""
        if 'message_stats' not in st.session_state:
            st.session_state.message_stats = []
            st.session_state.total_stats = {
                'input_tokens': 0,
                'output_tokens': 0,
                'total_tokens': 0,
                'total_cost': 0.0
            }
        
        with st.expander("📊 Token Usage Statistics", expanded=False):
            # Mostra i totali dalla session state
            cols = st.columns(4)
            with cols[0]:
                st.metric("Input Tokens", st.session_state.total_stats['input_tokens'])
            with cols[1]:
                st.metric("Output Tokens", st.session_state.total_stats['output_tokens'])
            with cols[2]:
                st.metric("Total Tokens", st.session_state.total_stats['total_tokens'])
            with cols[3]:
                st.metric("Cost ($)", f"${st.session_state.total_stats['total_cost']:.4f}")
            
            # Mostra history completa
            if st.session_state.message_stats:
                st.markdown("### History")
                df = pd.DataFrame(st.session_state.message_stats)
                # Formatta la colonna cost per mostrare 4 decimali
                if 'cost' in df.columns:
                    df['cost'] = df['cost'].apply(lambda x: f"${x:.4f}")
                st.dataframe(
                    df.sort_values('timestamp', ascending=False),
                    use_container_width=True
                )
    
    def _handle_gpt4o_completion(self, messages: List[Dict], model: str) -> Generator[str, None, None]:
        """Gestisce le chiamate ai modelli GPT-4o."""
        try:
            self._enforce_rate_limit(model)
            
            # Prima facciamo una chiamata non-streaming per ottenere l'usage
            usage_response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False,
                max_tokens=4096
            )
            
            # Calcoliamo il costo prima di usarlo
            cost = self.calculate_cost(
                model,
                usage_response.usage.prompt_tokens,
                usage_response.usage.completion_tokens
            )
            
            # Aggiorniamo l'usage dai dati ricevuti
            if hasattr(usage_response, 'usage'):
                self.update_message_stats(
                    model,
                    usage_response.usage.prompt_tokens,
                    usage_response.usage.completion_tokens,
                    cost
                )
            
            # Poi facciamo la chiamata streaming per la risposta effettiva
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=4096
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = f"Error with {model}: {str(e)}"
            st.error(error_msg)
            yield error_msg
    
    def _handle_o1_completion(self, messages: List[Dict], model: str) -> Generator[str, None, None]:
        """Gestisce le chiamate ai modelli o1."""
        try:
            self._enforce_rate_limit(model)
            
            # Prima facciamo una chiamata non-streaming per ottenere l'usage
            usage_response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=False,
                max_completion_tokens=32768 if model == "o1-preview" else 65536
            )
            
            # Calcoliamo il costo prima di usarlo
            cost = self.calculate_cost(
                model,
                usage_response.usage.prompt_tokens,
                usage_response.usage.completion_tokens
            )
            
            # Aggiorniamo l'usage dai dati ricevuti
            if hasattr(usage_response, 'usage'):
                self.update_message_stats(
                    model,
                    usage_response.usage.prompt_tokens,
                    usage_response.usage.completion_tokens,
                    cost  # Ora cost è definito
                )
            
            # Poi facciamo la chiamata streaming per la risposta effettiva
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
            error_msg = f"Error with {model}: {str(e)}"
            st.error(error_msg)
            yield error_msg

    def _handle_claude_completion_with_user_control(self, messages: List[Dict], 
                                           placeholder: st.empty) -> Generator[str, None, None]:
        for attempt in range(self.MAX_RETRIES):
            try:
                self._enforce_rate_limit("claude-3-5-sonnet-20241022")
                
                # Estrai il messaggio di sistema se presente
                system_message = None
                filtered_messages = []
                for msg in messages:
                    if msg["role"] == "system":
                        system_message = msg["content"]
                    else:
                        filtered_messages.append({
                            "role": msg["role"],
                            "content": msg["content"]
                        })
                
                # Crea la richiesta per Claude con il formato corretto
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    messages=filtered_messages,
                    system=system_message if system_message else None,  # Passa il system message come parametro separato
                    stream=True
                )
                
                # Track Claude usage
                if hasattr(response, 'usage'):
                    tokens = response.usage.input_tokens + response.usage.output_tokens
                    cost = self.calculate_cost("claude-3-5-sonnet-20241022", 
                                            response.usage.input_tokens,
                                            response.usage.output_tokens)
                    self.update_message_stats(
                        "claude-3-5-sonnet-20241022",
                        response.usage.input_tokens,
                        response.usage.output_tokens,
                        cost
                    )
                
                for chunk in response:
                    if chunk.type == 'content_block_delta':
                        yield chunk.delta.text
                        
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

    def _encode_image_to_base64(self, image_data: Union[str, bytes, Image.Image]) -> str:
        """
        Converte un'immagine in base64.
        
        Args:
            image_data: Può essere un path, bytes o un'immagine PIL
            
        Returns:
            str: Stringa base64 dell'immagine
        """
        if isinstance(image_data, str):
            # Se è un path file
            with open(image_data, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        elif isinstance(image_data, bytes):
            # Se sono bytes diretti
            return base64.b64encode(image_data).decode('utf-8')
        elif isinstance(image_data, Image.Image):
            # Se è un'immagine PIL
            buffered = BytesIO()
            image_data.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode('utf-8')
        else:
            raise ValueError("Formato immagine non supportato")
    
    def prepare_prompt(self, prompt: str, analysis_type: Optional[str] = None,
                file_content: Optional[str] = None, 
                context: Optional[str] = None,
                model: str = "claude-3-5-sonnet-20241022",
                image: Optional[Union[str, bytes, Image.Image]] = None) -> List[Dict]:
        """
        Prepara il prompt includendo il contesto dei file e le immagini.
        """
        messages = []
        
        # System message se supportato
        if self.model_limits[model]['supports_system_message']:
            messages.append({
                "role": "system",
                "content": "Sei un assistente esperto in analisi del codice e delle immagini."
            })

        # Per Grok Vision, formatta correttamente il messaggio con l'immagine
        if model == "grok-vision-beta" and image is not None:
            try:
                image_base64 = self._encode_image_to_base64(image)
                messages.append({
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                })
            except Exception as e:
                st.error(f"Errore nel processare l'immagine: {str(e)}")
                messages.append({
                    "role": "user",
                    "content": prompt
                })
        else:
            # Gestione normale per altri modelli
            main_content = prompt
            if file_content:
                main_content = f"File content:\n```\n{file_content}\n```\n\n{prompt}"
            if context:
                main_content += f"\nAdditional context: {context}"
            
            messages.append({
                "role": "user",
                "content": main_content
            })

        return messages

    def process_image_request(self, image: Union[str, bytes, Image.Image], 
                        prompt: str) -> Generator[str, None, None]:
        """
        Processa una richiesta specifica per l'analisi di immagini.
        """
        messages = self.prepare_prompt(
            prompt=prompt,
            model="grok-vision-beta",
            image=image
        )

        try:
            completion = self.grok_client.chat.completions.create(
                model="grok-vision-beta",
                messages=messages,
                stream=True
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = f"Errore nell'analisi dell'immagine: {str(e)}"
            st.error(error_msg)
            yield error_msg
    
    def process_request(self, prompt: str, analysis_type: Optional[str] = None,
                   file_content: Optional[str] = None, 
                   context: Optional[str] = None,
                   image: Optional[str] = None) -> Generator[str, None, None]:
        """Processa una richiesta completa con controllo utente sul retry e fallback."""
        model = st.session_state.current_model
        messages = self.prepare_prompt(
            prompt=prompt,
            analysis_type=analysis_type,
            file_content=file_content,
            context=context,
            model=model,
            image=image
        )
        
        # Placeholder per i controlli utente
        placeholder = st.empty()
        
        try:
            if model.startswith('grok'):
                yield from self._handle_grok_completion(messages, model)
            elif model.startswith('o1'):
                yield from self._handle_o1_completion(messages, model)
            elif model.startswith('gpt-4o'):
                yield from self._handle_gpt4o_completion(messages, model)
            else:
                yield from self._handle_claude_completion_with_user_control(messages, placeholder)
                
        except Exception as e:
            error_msg = f"Errore generale: {str(e)}"
            st.error(error_msg)
            with placeholder.container():
                if st.button("🔄 Riprova con un altro modello"):
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