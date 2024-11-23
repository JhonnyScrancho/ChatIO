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
            
        context = "Files disponibili:\n\n"
        
        # Prima il file selezionato, se presente
        if selected_file and selected_file in files:
            file_info = files[selected_file]
            context += f"File selezionato - {selected_file}:\n```{file_info['language']}\n{file_info['content']}\n```\n\n"
        
        # Poi gli altri file
        for filename, file_info in files.items():
            if filename != selected_file:
                context += f"File: {filename}\n```{file_info['language']}\n{file_info['content']}\n```\n\n"
                
        return context
    
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
        
        # Aggiungi system message se supportato
        if self.model_limits[model]['supports_system_message']:
            system_content = "Sei un assistente esperto in analisi del codice. "
            if analysis_type and analysis_type in self.system_templates:
                template = self.system_templates[analysis_type]
                system_content += f"{template['role']} Focus su: {', '.join(template['focus'])}"
            
            messages.append({
                "role": "system",
                "content": system_content
            })
        
        # Prepara il contenuto principale
        main_content = []
        
        # Aggiungi il contesto se presente
        if context:
            main_content.append(context)
        
        # Aggiungi il prompt dell'utente
        main_content.append(prompt)
        
        # Aggiungi il file_content specifico se presente
        if file_content:
            main_content.append(f"\nFile analizzato:\n```\n{file_content}\n```")
        
        # Unisci tutto il contenuto
        final_content = "\n\n".join(main_content)
        
        # Aggiungi il messaggio utente
        messages.append({
            "role": "user",
            "content": final_content
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
        """Gestisce le chiamate ai modelli OpenAI."""
        try:
            self._enforce_rate_limit(model)
            
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_tokens=32768 if model == "o1-preview" else 65536
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = f"Errore con {model}: {str(e)}"
            st.error(error_msg)
            # Non facciamo più il fallback automatico qui, lo gestiamo nel main
            yield error_msg
    
    def _handle_claude_completion(self, messages: List[Dict], system_message: str = None) -> Generator[str, None, None]:
        """Gestisce le chiamate a Claude."""
        try:
            self._enforce_rate_limit("claude-3-5-sonnet-20241022")
            
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4096,
                temperature=0.7,
                system=system_message,
                messages=messages,
                stream=True
            )
            
            for chunk in response:
                if chunk.delta.text:
                    yield chunk.delta.text
                    
        except Exception as e:
            error_msg = f"Errore Claude: {str(e)}"
            st.error(error_msg)
            yield error_msg
    
    def process_request(self, prompt: str, messages: List[Dict[str, str]] = None, 
                   model: str = None, context: str = None) -> Generator[str, None, None]:
        """
        Processa una richiesta completa.
        
        Args:
            prompt: Il prompt dell'utente
            messages: Lista di messaggi formattati (opzionale)
            model: Il modello da usare (opzionale)
            context: Contesto aggiuntivo (opzionale)
        """
        if model is None:
            model = "o1-mini"  # default model
        
        try:
            if model.startswith('o1'):
                # Per OpenAI, usiamo il formato messages
                if messages is None:
                    messages = [
                        {"role": "system", "content": "Sei un assistente esperto in analisi del codice."},
                        {"role": "user", "content": prompt}
                    ]
                
                return self._handle_o1_completion(messages, model)
            else:
                # Per Claude, prepariamo il messaggio nel suo formato
                system_message = None
                user_messages = []
                
                if messages:
                    for msg in messages:
                        if msg["role"] == "system":
                            system_message = msg["content"]
                        elif msg["role"] == "user":
                            user_messages.append({
                                "role": "user",
                                "content": [{"type": "text", "text": msg["content"]}]
                            })
                else:
                    user_messages = [{
                        "role": "user",
                        "content": [{"type": "text", "text": prompt}]
                    }]
                
                return self._handle_claude_completion(user_messages, system_message)
                
        except Exception as e:
            raise Exception(f"Errore nel processare la richiesta: {str(e)}")
    
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