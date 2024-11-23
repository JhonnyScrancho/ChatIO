"""
LLM integration for Allegro IO Code Assistant.
Manages interactions with OpenAI and Anthropic models with proper error handling,
rate limiting, and model-specific optimizations.
"""

import streamlit as st
from typing import Dict, Optional, Tuple, Generator, List, Any, Union
from openai import OpenAI
from anthropic import Anthropic
import time
from datetime import datetime
import json
import tiktoken
import re
from dataclasses import dataclass
from enum import Enum

class AnalysisType(Enum):
    CODE_REVIEW = "code_review"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    DEBUG = "debug"
    GENERAL = "general"

@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_cost: float

class LLMManager:
    """Gestisce le interazioni con i modelli LLM."""
    
    def __init__(self):
        """Inizializza le connessioni API e le configurazioni."""
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
                'supports_system_message': True,
                'supports_functions': False,
                'token_encoding': 'cl100k_base'
            },
            'o1-mini': {
                'max_tokens': 65536,
                'context_window': 128000,
                'supports_files': False,
                'supports_system_message': True,
                'supports_functions': False,
                'token_encoding': 'cl100k_base'
            },
            'claude-3-5-sonnet-20241022': {
                'max_tokens': 200000,
                'context_window': 200000,
                'supports_files': True,
                'supports_system_message': True,
                'supports_functions': True,
                'token_encoding': 'cl100k_base'
            }
        }
        
        # Template di sistema per diversi tipi di analisi
        self.system_templates = {
            AnalysisType.CODE_REVIEW: {
                'role': "You are a senior software engineer performing a thorough code review.",
                'focus': ["Code quality", "Design patterns", "Potential issues"],
                'guidelines': [
                    "Focus on maintainability and readability",
                    "Identify potential bugs and edge cases",
                    "Suggest performance improvements"
                ]
            },
            AnalysisType.ARCHITECTURE: {
                'role': "You are a software architect analyzing code structure.",
                'focus': ["Architectural patterns", "SOLID principles", "Scalability"],
                'guidelines': [
                    "Evaluate system design patterns",
                    "Assess component coupling",
                    "Review dependency management"
                ]
            },
            AnalysisType.SECURITY: {
                'role': "You are a security expert analyzing code.",
                'focus': ["Vulnerabilities", "Security best practices", "Potential risks"],
                'guidelines': [
                    "Check for common security vulnerabilities",
                    "Review authentication and authorization",
                    "Identify data protection issues"
                ]
            },
            AnalysisType.DEBUG: {
                'role': "You are a debugging expert helping identify and fix issues.",
                'focus': ["Error analysis", "Problem solving", "Code optimization"],
                'guidelines': [
                    "Analyze error patterns",
                    "Suggest debugging approaches",
                    "Recommend optimization strategies"
                ]
            }
        }
        
        # Cache per rate limiting
        self._last_call_time = {}
        self._call_count = {}
        self._reset_time = {}
        
        # Cache per i tokenizer
        self._tokenizers = {}

    def _get_tokenizer(self, model: str):
        """
        Ottiene il tokenizer appropriato per il modello.
        
        Args:
            model: Nome del modello
            
        Returns:
            tokenizer: Istanza del tokenizer
        """
        if model not in self._tokenizers:
            encoding_name = self.model_limits[model]['token_encoding']
            self._tokenizers[model] = tiktoken.get_encoding(encoding_name)
        return self._tokenizers[model]

    def count_tokens(self, text: str, model: str) -> int:
        """
        Conta i token in un testo per un dato modello.
        
        Args:
            text: Testo da analizzare
            model: Nome del modello
            
        Returns:
            int: Numero di token
        """
        tokenizer = self._get_tokenizer(model)
        return len(tokenizer.encode(text))

    def get_files_context(self, files: Dict[str, Any], selected_file: Optional[str] = None,
                         max_tokens: Optional[int] = None) -> str:
        """
        Prepara il contesto con tutti i file, evidenziando quello selezionato.
        
        Args:
            files: Dizionario dei file caricati
            selected_file: Nome del file selezionato (opzionale)
            max_tokens: Limite massimo di token (opzionale)
            
        Returns:
            str: Contesto formattato con tutti i file
        """
        if not files:
            return ""
            
        context_parts = ["Files disponibili:\n\n"]
        current_tokens = 0
        
        # Prima il file selezionato, se presente
        if selected_file and selected_file in files:
            file_info = files[selected_file]
            content = f"File selezionato - {selected_file}:\n```{file_info['language']}\n{file_info['content']}\n```\n\n"
            if max_tokens:
                tokens = self.count_tokens(content, "o1-mini")  # Usa o1-mini come riferimento
                if current_tokens + tokens > max_tokens:
                    content = self._truncate_to_tokens(content, max_tokens - current_tokens, "o1-mini")
            context_parts.append(content)
            current_tokens += self.count_tokens(content, "o1-mini")
        
        # Poi gli altri file
        for filename, file_info in files.items():
            if filename != selected_file:
                content = f"File: {filename}\n```{file_info['language']}\n{file_info['content']}\n```\n\n"
                if max_tokens:
                    remaining_tokens = max_tokens - current_tokens
                    if remaining_tokens <= 0:
                        break
                    tokens = self.count_tokens(content, "o1-mini")
                    if current_tokens + tokens > max_tokens:
                        content = self._truncate_to_tokens(content, remaining_tokens, "o1-mini")
                context_parts.append(content)
                current_tokens += self.count_tokens(content, "o1-mini")
                
        return "".join(context_parts)

    def _truncate_to_tokens(self, text: str, max_tokens: int, model: str) -> str:
        """
        Tronca il testo per rispettare il limite di token.
        
        Args:
            text: Testo da troncare
            max_tokens: Numero massimo di token
            model: Nome del modello
            
        Returns:
            str: Testo troncato
        """
        tokenizer = self._get_tokenizer(model)
        tokens = tokenizer.encode(text)
        if len(tokens) <= max_tokens:
            return text
        
        truncated_tokens = tokens[:max_tokens-3]  # Lascia spazio per "[...]"
        truncated_text = tokenizer.decode(truncated_tokens)
        return truncated_text + "[...]"

    def prepare_system_message(self, analysis_type: Optional[Union[str, AnalysisType]] = None) -> str:
        """
        Prepara il messaggio di sistema in base al tipo di analisi.
        
        Args:
            analysis_type: Tipo di analisi richiesta
            
        Returns:
            str: Messaggio di sistema formattato
        """
        if isinstance(analysis_type, str):
            try:
                analysis_type = AnalysisType(analysis_type)
            except ValueError:
                analysis_type = AnalysisType.GENERAL
        
        base_message = "You are a code analysis assistant. "
        
        if analysis_type and analysis_type in self.system_templates:
            template = self.system_templates[analysis_type]
            guidelines = "\n- " + "\n- ".join(template['guidelines'])
            return (f"{base_message}{template['role']} "
                   f"Focus on: {', '.join(template['focus'])}. "
                   f"Guidelines:{guidelines}")
            
        return base_message + "Help analyze and explain code, suggesting improvements and best practices."
    
    def prepare_messages(self, prompt: str, context: Optional[str] = None,
                        analysis_type: Optional[Union[str, AnalysisType]] = None) -> List[Dict[str, str]]:
        """
        Prepara i messaggi per la richiesta all'LLM.
        
        Args:
            prompt: Prompt dell'utente
            context: Contesto (es. contenuto dei file)
            analysis_type: Tipo di analisi richiesta
            
        Returns:
            List[Dict[str, str]]: Lista di messaggi formattati
        """
        messages = []
        
        # Aggiungi sempre il messaggio di sistema
        messages.append({
            "role": "system",
            "content": self.prepare_system_message(analysis_type)
        })
        
        # Prepara il contenuto principale
        main_content = []
        
        # Aggiungi il contesto se presente
        if context:
            main_content.append(context)
        
        # Aggiungi il prompt dell'utente
        main_content.append(prompt)
        
        # Unisci il contenuto e aggiungi come messaggio utente
        messages.append({
            "role": "user",
            "content": "\n\n".join(main_content)
        })
        
        return messages
    
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
    
    def process_request(self, prompt: str, context: Optional[str] = None, 
                       model: str = "o1-mini",
                       analysis_type: Optional[Union[str, AnalysisType]] = None) -> Generator[str, None, None]:
        """
        Processa una richiesta all'LLM.
        
        Args:
            prompt: Prompt dell'utente
            context: Contesto opzionale (es. contenuto dei file)
            model: Nome del modello da utilizzare
            analysis_type: Tipo di analisi richiesta
            
        Yields:
            str: Chunks della risposta
        """
        try:
            # Verifica limiti del contesto
            if context:
                context_tokens = self.count_tokens(context, model)
                model_limit = self.model_limits[model]['context_window']
                if context_tokens > model_limit * 0.8:  # Usa 80% come limite sicuro
                    context = self._truncate_to_tokens(context, int(model_limit * 0.7), model)
                    yield "⚠️ Il contesto è stato troncato per rispettare i limiti del modello.\n\n"
            
            # Prepara i messaggi
            messages = self.prepare_messages(prompt, context, analysis_type)
            
            # Gestisci la richiesta in base al modello
            if model.startswith('claude'):
                claude_messages = [{
                    "role": "user",
                    "content": messages[-1]["content"]
                }]
                
                for chunk in self._handle_claude_completion(
                    messages=claude_messages,
                    system_message=messages[0]["content"]
                ):
                    yield chunk
            else:
                for chunk in self._handle_o1_completion(messages, model):
                    yield chunk
                    
        except Exception as e:
            error_msg = f"Errore nel processare la richiesta con {model}: {str(e)}"
            st.error(error_msg)
            yield error_msg
    
    def _handle_o1_completion(self, messages: List[Dict], model: str) -> Generator[str, None, None]:
        """
        Gestisce le chiamate ai modelli OpenAI.
        
        Args:
            messages: Lista di messaggi formattati
            model: Nome del modello OpenAI
            
        Yields:
            str: Chunks della risposta
        """
        try:
            self._enforce_rate_limit(model)
            
            # Monitora l'uso dei token
            input_tokens = sum(self.count_tokens(msg["content"], model) for msg in messages)
            
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=[{
                    "role": msg["role"],
                    "content": msg["content"]
                } for msg in messages],
                stream=True,
                temperature=0.7,
                max_tokens=min(
                    self.model_limits[model]['max_tokens'],
                    self.model_limits[model]['context_window'] - input_tokens
                )
            )
            
            output_text = ""
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    output_text += content
                    yield content
            
            # Aggiorna statistiche di utilizzo
            output_tokens = self.count_tokens(output_text, model)
            self._update_usage_stats(model, input_tokens, output_tokens)
                    
        except Exception as e:
            error_msg = f"Errore OpenAI: {str(e)}"
            st.error(error_msg)
            yield error_msg
    
    def _handle_claude_completion(self, messages: List[Dict], 
                                system_message: Optional[str] = None) -> Generator[str, None, None]:
        """
        Gestisce le chiamate a Claude.
        
        Args:
            messages: Lista di messaggi formattati
            system_message: Messaggio di sistema opzionale
            
        Yields:
            str: Chunks della risposta
        """
        try:
            self._enforce_rate_limit("claude-3-5-sonnet-20241022")
            
            # Monitora l'uso dei token
            input_tokens = sum(self.count_tokens(msg["content"], "claude-3-5-sonnet-20241022") 
                             for msg in messages)
            if system_message:
                input_tokens += self.count_tokens(system_message, "claude-3-5-sonnet-20241022")
            
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=min(
                    4096,
                    self.model_limits["claude-3-5-sonnet-20241022"]['context_window'] - input_tokens
                ),
                temperature=0.7,
                system=system_message,
                messages=messages,
                stream=True
            )
            
            output_text = ""
            for chunk in response:
                if chunk.delta.text:
                    content = chunk.delta.text
                    output_text += content
                    yield content
            
            # Aggiorna statistiche di utilizzo
            output_tokens = self.count_tokens(output_text, "claude-3-5-sonnet-20241022")
            self._update_usage_stats("claude-3-5-sonnet-20241022", input_tokens, output_tokens)
                    
        except Exception as e:
            error_msg = f"Errore Claude: {str(e)}"
            st.error(error_msg)
            yield error_msg

    def _update_usage_stats(self, model: str, input_tokens: int, output_tokens: int):
        """
        Aggiorna le statistiche di utilizzo nella session state.
        
        Args:
            model: Nome del modello
            input_tokens: Numero di token in input
            output_tokens: Numero di token in output
        """
        if 'model_usage' not in st.session_state:
            st.session_state.model_usage = {}
        
        if model not in st.session_state.model_usage:
            st.session_state.model_usage[model] = {
                'calls': 0,
                'input_tokens': 0,
                'output_tokens': 0,
                'total_cost': 0.0
            }
        
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        
        stats = st.session_state.model_usage[model]
        stats['calls'] += 1
        stats['input_tokens'] += input_tokens
        stats['output_tokens'] += output_tokens
        stats['total_cost'] += cost
        
        # Aggiorna anche i totali globali
        st.session_state.token_count = (st.session_state.get('token_count', 0) + 
                                      input_tokens + output_tokens)
        st.session_state.cost = st.session_state.get('cost', 0.0) + cost
    
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
            
        usage = st.session_state.get('model_usage', {}).get(model, {
            'calls': 0,
            'input_tokens': 0,
            'output_tokens': 0,
            'total_cost': 0.0
        })
            
        return {
            "limits": self.model_limits[model],
            "costs": self.cost_map[model],
            "current_usage": {
                "calls_last_minute": self._call_count.get(model, 0),
                "last_call": datetime.fromtimestamp(
                    self._last_call_time.get(model, 0)
                ).strftime('%Y-%m-%d %H:%M:%S'),
                "total_calls": usage['calls'],
                "total_tokens": usage['input_tokens'] + usage['output_tokens'],
                "total_cost": usage['total_cost']
            }
        }

    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riepilogo dell'utilizzo di tutti i modelli.
        
        Returns:
            Dict[str, Any]: Riepilogo dell'utilizzo
        """
        usage = st.session_state.get('model_usage', {})
        
        summary = {
            'total_calls': sum(model['calls'] for model in usage.values()),
            'total_tokens': sum(model['input_tokens'] + model['output_tokens'] 
                              for model in usage.values()),
            'total_cost': sum(model['total_cost'] for model in usage.values()),
            'models': {
                model: {
                    'calls': stats['calls'],
                    'tokens': stats['input_tokens'] + stats['output_tokens'],
                    'cost': stats['total_cost']
                }
                for model, stats in usage.items()
            }
        }
        
        return summary

    def estimate_tokens(self, text: str, model: str) -> int:
        """
        Stima il numero di token in un testo.
        
        Args:
            text: Testo da analizzare
            model: Nome del modello
            
        Returns:
            int: Numero stimato di token
        """
        return self.count_tokens(text, model)

    def estimate_cost(self, text: str, model: str, 
                     expected_output_ratio: float = 1.5) -> float:
        """
        Stima il costo di una richiesta.
        
        Args:
            text: Testo da analizzare
            model: Nome del modello
            expected_output_ratio: Rapporto atteso tra output e input tokens
            
        Returns:
            float: Costo stimato in USD
        """
        input_tokens = self.count_tokens(text, model)
        estimated_output_tokens = int(input_tokens * expected_output_ratio)
        
        return self.calculate_cost(model, input_tokens, estimated_output_tokens)

    async def aprocess_request(self, prompt: str, context: Optional[str] = None,
                             model: str = "o1-mini",
                             analysis_type: Optional[Union[str, AnalysisType]] = None) -> Generator[str, None, None]:
        """
        Versione asincrona di process_request.
        
        Args:
            prompt: Prompt dell'utente
            context: Contesto opzionale
            model: Nome del modello
            analysis_type: Tipo di analisi
            
        Yields:
            str: Chunks della risposta
        """
        # Implementazione asincrona simile a process_request
        # Utile per future integrazioni con framework asincroni
        async for chunk in self._ahandle_request(prompt, context, model, analysis_type):
            yield chunk

    async def _ahandle_request(self, prompt: str, context: Optional[str],
                              model: str, analysis_type: Optional[Union[str, AnalysisType]]) -> Generator[str, None, None]:
        """
        Handler asincrono interno per le richieste.
        
        Args:
            prompt: Prompt dell'utente
            context: Contesto opzionale
            model: Nome del modello
            analysis_type: Tipo di analisi
            
        Yields:
            str: Chunks della risposta
        """
        # Implementazione del handler asincrono
        # Da implementare quando necessario
        pass