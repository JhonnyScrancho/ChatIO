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
                'supports_functions': False
            },
            'o1-mini': {
                'max_tokens': 65536,
                'context_window': 128000,
                'supports_files': False,
                'supports_system_message': True,
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
                'role': "You are a senior software engineer performing a thorough code review.",
                'focus': ["Code quality", "Design patterns", "Potential issues"]
            },
            'architecture': {
                'role': "You are a software architect analyzing code structure.",
                'focus': ["Architectural patterns", "SOLID principles", "Scalability"]
            },
            'security': {
                'role': "You are a security expert analyzing code.",
                'focus': ["Vulnerabilities", "Security best practices", "Potential risks"]
            },
            'debug': {
                'role': "You are a debugging expert helping identify and fix issues.",
                'focus': ["Error analysis", "Problem solving", "Code optimization"]
            }
        }
        
        # Cache per rate limiting
        self._last_call_time = {}
        self._call_count = {}
        self._reset_time = {}
    
    def get_files_context(self, files: Dict[str, Any], selected_file: Optional[str] = None) -> str:
        """
        Prepara il contesto con tutti i file, evidenziando quello selezionato.
        
        Args:
            files: Dizionario dei file caricati
            selected_file: Nome del file selezionato (opzionale)
            
        Returns:
            str: Contesto formattato con tutti i file
        """
        if not files:
            return ""
            
        context_parts = ["Files disponibili:\n\n"]
        
        # Prima il file selezionato, se presente
        if selected_file and selected_file in files:
            file_info = files[selected_file]
            context_parts.append(
                f"File selezionato - {selected_file}:\n"
                f"```{file_info['language']}\n{file_info['content']}\n```\n\n"
            )
        
        # Poi gli altri file
        for filename, file_info in files.items():
            if filename != selected_file:
                context_parts.append(
                    f"File: {filename}\n"
                    f"```{file_info['language']}\n{file_info['content']}\n```\n\n"
                )
                
        return "".join(context_parts)
    
    def prepare_system_message(self, analysis_type: Optional[str] = None) -> str:
        """
        Prepara il messaggio di sistema in base al tipo di analisi.
        
        Args:
            analysis_type: Tipo di analisi richiesta
            
        Returns:
            str: Messaggio di sistema formattato
        """
        base_message = "You are a code analysis assistant. "
        
        if analysis_type and analysis_type in self.system_templates:
            template = self.system_templates[analysis_type]
            return f"{base_message}{template['role']} Focus on: {', '.join(template['focus'])}"
            
        return base_message + "Help analyze and explain code, suggesting improvements and best practices."
    
    def prepare_messages(self, prompt: str, context: Optional[str] = None,
                        analysis_type: Optional[str] = None) -> List[Dict[str, str]]:
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
                       model: str = "o1-mini") -> Generator[str, None, None]:
        """
        Processa una richiesta all'LLM.
        
        Args:
            prompt: Prompt dell'utente
            context: Contesto opzionale (es. contenuto dei file)
            model: Nome del modello da utilizzare
            
        Yields:
            str: Chunks della risposta
        """
        try:
            # Prepara i messaggi
            messages = self.prepare_messages(prompt, context)
            
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
            
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=[{
                    "role": msg["role"],
                    "content": msg["content"]
                } for msg in messages],
                stream=True,
                temperature=0.7,
                max_tokens=self.model_limits[model]['max_tokens']
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
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
            
            # Prepara i messaggi nel formato corretto per Claude
            claude_messages = []
            for msg in messages:
                claude_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0.7,
                system=system_message,
                messages=claude_messages,
                stream=True
            )
            
            for chunk in response:
                if chunk.delta.text:
                    yield chunk.delta.text
                    
        except Exception as e:
            error_msg = f"Errore Claude: {str(e)}"
            st.error(error_msg)
            yield error_msg
    
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