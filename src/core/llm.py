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
        
        # Stima tokens (1 token ~ 4 caratteri)
        estimated_tokens = content_length // 4
        
        # Se supera i limiti di o1-preview, usa Claude
        if estimated_tokens > 32000:
            return "claude-3-5-sonnet-20241022"
        
        # Per task complessi usa o1-preview
        if task_type in ["architecture", "review", "security"]:
            return "o1-preview"
        
        # Per task più semplici usa o1-mini
        return "o1-mini"
    
    def prepare_prompt(self, prompt: str, analysis_type: Optional[str] = None,
                  file_content: Optional[str] = None, 
                  context: Optional[str] = None,
                  model: str = "claude-3-5-sonnet-20241022") -> Dict[str, Any]:
        """
        Prepara il prompt completo in base al modello.
        """
        messages = []
        
        # Aggiungi system message se supportato e richiesto
        if self.model_limits[model]['supports_system_message'] and analysis_type:
            template = self.system_templates[analysis_type]
            system_msg = {
                "role": "system",
                "content": f"{template['role']} Focus su: {', '.join(template['focus'])}"
            }
            messages.append(system_msg)
        
        # Prepara il contenuto principale
        main_content = prompt
        
        # Aggiungi il contenuto del file se presente
        if file_content:
            file_section = f"\nFile content:\n```\n{file_content}\n```"
            main_content += file_section
        
        # Aggiungi il contesto se presente
        if context:
            context_section = f"\nContext: {context}"
            main_content += context_section
        
        # Aggiungi il messaggio utente
        messages.append({
            "role": "user",
            "content": main_content
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
            # Fallback a Claude in caso di errore
            yield from self._handle_claude_completion(messages)
    
    def _handle_claude_completion(self, messages: List[Dict]) -> Generator[str, None, None]:
        """
        Gestisce le chiamate a Claude.
        
        Args:
            messages: Lista di messaggi
            
        Yields:
            str: Chunks della risposta
        """
        try:
            self._enforce_rate_limit("claude-3-5-sonnet-20241022")
            
            # Converti i messaggi nel formato corretto per Claude 3
            claude_messages = []
            system_message = None
            
            for msg in messages:
                if msg["role"] == "system":
                    system_message = [{
                        "type": "text",
                        "text": msg["content"]
                    }]
                else:
                    claude_messages.append({
                        "role": msg["role"],
                        "content": [{
                            "type": "text",
                            "text": msg["content"]
                        }]
                    })
            
            try:
                # Debug: stampa i messaggi prima dell'invio
                st.write("Debug - System message:", system_message)
                st.write("Debug - Messages:", claude_messages)
                
                response = self.anthropic_client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=4096,
                    temperature=0.7,
                    system=system_message,  # Ora è una lista di oggetti content
                    messages=claude_messages,
                    stream=True
                )
                
                for chunk in response:
                    if chunk.delta.text:
                        yield chunk.delta.text
                        
            except Exception as e:
                st.error(f"Errore nella chiamata API: {str(e)}")
                yield f"Mi dispiace, si è verificato un errore: {str(e)}"
                
        except Exception as e:
            error_msg = f"Errore Claude: {str(e)}"
            st.error(error_msg)
            yield error_msg

    
    def process_request(self, prompt: str, analysis_type: Optional[str] = None,
                       file_content: Optional[str] = None, 
                       context: Optional[str] = None) -> Generator[str, None, None]:
        """
        Processa una richiesta completa.
        
        Args:
            prompt: Prompt dell'utente
            analysis_type: Tipo di analisi
            file_content: Contenuto del file
            context: Contesto aggiuntivo
            
        Yields:
            str: Chunks della risposta
        """
        # Determina se il task richiede gestione file
        requires_file_handling = bool(file_content)
        
        # Seleziona il modello appropriato
        if analysis_type and file_content:
            model = self.select_model(
                analysis_type, 
                len(file_content), 
                requires_file_handling
            )
        else:
            model = st.session_state.current_model
        
        # Prepara i messaggi
        messages = self.prepare_prompt(
            prompt=prompt,
            analysis_type=analysis_type,
            file_content=file_content,
            context=context,
            model=model
        )
        
        # Processa la richiesta con il modello appropriato
        if model.startswith('o1'):
            yield from self._handle_o1_completion(messages, model)
        else:
            yield from self._handle_claude_completion(messages)
    
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