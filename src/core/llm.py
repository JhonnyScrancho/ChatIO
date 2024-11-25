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
import logging

class LLMManager:
    """Gestisce le interazioni con i modelli LLM."""
    
    def __init__(self):
        """Inizializza le connessioni API e le configurazioni."""
        self.logger = logging.getLogger(__name__)
        try:
            self.openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
            self.anthropic_client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        except Exception as e:
            st.error(f"Errore nell'inizializzazione delle API: {str(e)}")
            raise
        
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
    
    def _log(self, message: str, level: str = "INFO"):
        """
        Gestisce il logging dell'applicazione.
        
        Args:
            message: Messaggio da loggare
            level: Livello di logging (INFO, ERROR, etc.)
        """
        if level.upper() == "ERROR":
            self.logger.error(message)
            st.error(message)
        elif level.upper() == "WARNING":
            self.logger.warning(message)
            st.warning(message)
        else:
            self.logger.info(message)
            if st.session_state.get('debug_mode', False):
                st.info(message)   
   
    def prepare_prompt(self, prompt: str, analysis_type: Optional[str] = None,
                      file_content: Optional[str] = None, 
                      context: Optional[str] = None,
                      model: str = "claude-3-5-sonnet-20241022") -> Dict[str, Any]:
        """
        Prepara il prompt completo in base al modello.
        
        Args:
            prompt: Prompt base
            analysis_type: Tipo di analisi
            file_content: Contenuto del file
            context: Contesto aggiuntivo
            model: Modello da utilizzare
            
        Returns:
            Dict[str, Any]: Messaggio formattato per il modello
        """
        messages = []
        system_content = None
        
        # Prepara il contenuto del sistema se supportato e richiesto
        if self.model_limits[model]['supports_system_message'] and analysis_type:
            template = self.system_templates[analysis_type]
            system_content = f"{template['role']} Focus su: {', '.join(template['focus'])}"
        
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
        
        # Formatta il messaggio in base al modello
        if model.startswith('claude'):
            if system_content:
                messages = [
                    {
                        "role": "system",
                        "content": system_content
                    },
                    {
                        "role": "user",
                        "content": main_content
                    }
                ]
            else:
                messages = [
                    {
                        "role": "user",
                        "content": main_content
                    }
                ]
        else:
            if system_content:
                messages = [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": main_content}
                ]
            else:
                messages = [{"role": "user", "content": main_content}]
        
        return {
            "messages": messages,
            "system": system_content
        }
    
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
    
    def _handle_o1_completion(self, messages: List[Dict], model: str, is_fallback: bool = False) -> Generator[str, None, None]:
        """
        Gestisce le chiamate ai modelli o1.
        
        Args:
            messages: Lista di messaggi
            model: Nome del modello o1
            is_fallback: Se True, non esegue ulteriori fallback
            
        Yields:
            str: Chunks della risposta
        """
        try:
            self._enforce_rate_limit(model)
            
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_completion_tokens=32768 if model == "o1-preview" else 65536,
                temperature=1
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = f"Errore con {model}: {str(e)}"
            st.error(error_msg)
            if not is_fallback:
                yield "Mi scuso per l'errore. Proverò con un modello alternativo.\n\n"
                for chunk in self._handle_claude_completion({"messages": messages}, is_fallback=True):
                    yield chunk
            else:
                yield "Mi dispiace, si è verificato un errore con entrambi i modelli."

    def _handle_claude_completion(self, prompt_data: Dict[str, Any], is_fallback: bool = False) -> Generator[str, None, None]:
        """
        Gestisce le chiamate a Claude con logging dettagliato.
        
        Args:
            prompt_data: Dizionario contenente i messaggi e il system prompt
            is_fallback: Se True, non esegue ulteriori fallback
            
        Yields:
            str: Chunks della risposta
        """
        MODEL = "claude-3-5-sonnet-20241022"
        
        try:
            # Log 1: Inizio della funzione
            st.info("🔄 Inizializzando chiamata Claude...")
            
            # Log 2: Verifica rate limiting
            st.info("👮 Verificando rate limits...")
            self._enforce_rate_limit("claude")
            
            # Log 3: Preparazione messaggi
            messages = []
            if system := prompt_data.get("system"):
                st.info("📝 System prompt trovato, aggiungendo...")
                messages.append({
                    "role": "system",
                    "content": system
                })
            
            # Log 4: Aggiunta messaggi utente
            st.info("📨 Preparazione messaggi utente...")
            for msg in prompt_data.get("messages", []):
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
            
            # Log 5: Debug struttura messaggi
            st.info("🔍 Struttura messaggi preparata:")
            st.write({
                "model": MODEL,
                "message_count": len(messages),
                "roles": [msg["role"] for msg in messages]
            })

            # Log 6: Inizio chiamata API
            st.info("🚀 Avvio chiamata API Claude...")
            
            stream = self.anthropic_client.messages.create(
                model=MODEL,
                messages=messages,
                stream=True,
                max_tokens=4096
            )
            
            # Log 7: Chiamata API riuscita
            st.success("✅ Connessione API stabilita, inizio streaming risposta...")
            
            # Log 8: Processo di streaming
            chunks_received = 0
            for chunk in stream:
                if chunk.type == "content_block_delta" and chunk.delta.text:
                    chunks_received += 1
                    if chunks_received % 10 == 0:  # Log ogni 10 chunks
                        st.info(f"📊 Ricevuti {chunks_received} chunks...")
                    yield chunk.delta.text
            
            # Log 9: Completamento streaming
            st.success(f"✅ Streaming completato. Totale chunks: {chunks_received}")
                        
        except Exception as e:
            # Log 10: Gestione errori dettagliata
            error_type = type(e).__name__
            error_msg = str(e)
            
            st.error(f"""❌ Errore Claude:
            - Tipo: {error_type}
            - Messaggio: {error_msg}
            - Traceback disponibile nei log del server
            """)
            
            # Log dello stack trace completo se in debug mode
            if st.session_state.get('debug_mode', False):
                import traceback
                st.error("🔍 Debug Stack Trace:")
                st.code(traceback.format_exc())
            
            if not is_fallback:
                st.warning("⚠️ Tentativo di fallback a modello alternativo...")
                yield "Mi scuso per l'errore. Proverò con un modello alternativo.\n\n"
                fallback_messages = [{"role": "user", "content": msg["content"]} 
                                for msg in prompt_data.get("messages", [])]
                for chunk in self._handle_o1_completion(fallback_messages, "o1-preview", is_fallback=True):
                    yield chunk
            else:
                st.error("❌ Fallback fallito. Impossibile completare la richiesta.")
                yield "Mi dispiace, si è verificato un errore con entrambi i modelli."
            
            # Log 11: Registrazione errore nel logger
            self.logger.error(f"Errore Claude: {error_type} - {error_msg}",
                            exc_info=True)

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
        try:
            requires_file_handling = bool(file_content)
            
            if analysis_type and file_content:
                model = self.select_model(
                    analysis_type, 
                    len(file_content), 
                    requires_file_handling
                )
            else:
                model = st.session_state.current_model
            
            prompt_data = self.prepare_prompt(
                prompt=prompt,
                analysis_type=analysis_type,
                file_content=file_content,
                context=context,
                model=model
            )
            
            if model.startswith('o1'):
                for chunk in self._handle_o1_completion(prompt_data["messages"], model):
                    yield chunk
            else:
                for chunk in self._handle_claude_completion(prompt_data):
                    yield chunk
                    
        except Exception as e:
            st.error(f"Errore generale: {str(e)}")
            yield "Si è verificato un errore. Per favore, riprova più tardi."
    
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
    
    def _validate_model_availability(self, model: str) -> bool:
        """
        Verifica la disponibilità di un modello.
        
        Args:
            model: Nome del modello da verificare
            
        Returns:
            bool: True se il modello è disponibile
        """
        if model not in self.model_limits:
            self._log(f"Modello {model} non supportato", "WARNING")
            return False
            
        if model.startswith('claude') and not hasattr(self, 'anthropic_client'):
            self._log("Client Anthropic non inizializzato", "ERROR")
            return False
            
        if model.startswith('o1') and not hasattr(self, 'openai_client'):
            self._log("Client OpenAI non inizializzato", "ERROR")
            return False
            
        return True
    
    def estimate_tokens(self, text: str) -> int:
        """
        Stima approssimativa del numero di token in un testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            int: Numero stimato di token
        """
        # Approssimazione semplice: 1 token ~= 4 caratteri
        return len(text) // 4
    
    def update_usage_stats(self, model: str, input_tokens: int, output_tokens: int):
        """
        Aggiorna le statistiche di utilizzo nella sessione.
        
        Args:
            model: Nome del modello utilizzato
            input_tokens: Numero di token in input
            output_tokens: Numero di token in output
        """
        if 'usage_stats' not in st.session_state:
            st.session_state.usage_stats = {
                'total_tokens': 0,
                'total_cost': 0.0,
                'models': {}
            }
        
        stats = st.session_state.usage_stats
        stats['total_tokens'] += (input_tokens + output_tokens)
        cost = self.calculate_cost(model, input_tokens, output_tokens)
        stats['total_cost'] += cost
        
        if model not in stats['models']:
            stats['models'][model] = {
                'calls': 0,
                'tokens': 0,
                'cost': 0.0
            }
        
        model_stats = stats['models'][model]
        model_stats['calls'] += 1
        model_stats['tokens'] += (input_tokens + output_tokens)
        model_stats['cost'] += cost
    
    def get_usage_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riepilogo dell'utilizzo.
        
        Returns:
            Dict[str, Any]: Statistiche di utilizzo
        """
        if 'usage_stats' not in st.session_state:
            return {
                'total_tokens': 0,
                'total_cost': 0.0,
                'models': {}
            }
        
        return st.session_state.usage_stats
    
    def reset_usage_stats(self):
        """Resetta le statistiche di utilizzo."""
        if 'usage_stats' in st.session_state:
            del st.session_state.usage_stats
    
    def handle_error(self, error: Exception, context: str = ""):
        """
        Gestisce gli errori in modo centralizzato.
        
        Args:
            error: Eccezione da gestire
            context: Contesto dell'errore
        """
        error_msg = f"Error in {context}: {str(error)}"
        self._log(error_msg, "ERROR")
        
        if 'error_log' not in st.session_state:
            st.session_state.error_log = []
            
        st.session_state.error_log.append({
            'timestamp': datetime.now().isoformat(),
            'error': str(error),
            'context': context,
            'type': type(error).__name__
        })
        
        # Notifica l'errore all'interfaccia
        st.error(f"Si è verificato un errore: {str(error)}")
        
        if st.session_state.get('debug_mode', False):
            st.exception(error)
    
    def cleanup(self):
        """Esegue le operazioni di pulizia necessarie."""
        # Resetta i contatori del rate limiting
        self._last_call_time = {}
        self._call_count = {}
        self._reset_time = {}
        
        # Chiude le connessioni dei client
        if hasattr(self, 'openai_client'):
            del self.openai_client
        
        if hasattr(self, 'anthropic_client'):
            del self.anthropic_client