"""
LLM integration for Allegro IO Code Assistant.
Manages interactions with OpenAI and Anthropic models.
"""

import streamlit as st
from typing import Dict, Optional, Tuple, Generator
from openai import OpenAI
from anthropic import Anthropic

class LLMManager:
    """Gestisce le interazioni con i modelli LLM."""
    
    def __init__(self):
        """Inizializza le connessioni API."""
        self.openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        self.anthropic_client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        
        # Costi per 1K tokens (in USD)
        self.cost_map = {
            'o1-preview': {'input': 0.01, 'output': 0.03},
            'o1-mini': {'input': 0.001, 'output': 0.002},
            'claude-3-5-sonnet': {'input': 0.008, 'output': 0.024}
        }
    
    def select_model(self, task_type: str, content_length: int) -> str:
        """
        Seleziona automaticamente il modello più appropriato.
        
        Args:
            task_type: Tipo di task (es. 'architecture', 'review', 'debug')
            content_length: Lunghezza del contenuto in caratteri
            
        Returns:
            str: Nome del modello selezionato
        """
        # Stima approssimativa dei token (1 token ~ 4 caratteri)
        estimated_tokens = content_length // 4
        
        if estimated_tokens > 32000:  # Limite massimo per o1-preview
            return "claude-3-5-sonnet"
        elif task_type in ["architecture", "review", "security"]:
            return "o1-preview"
        else:
            return "o1-mini"
    
    def _prepare_messages(self, prompt: str, content: Optional[str] = None,
                         context: Optional[str] = None) -> list:
        """
        Prepara i messaggi per l'API.
        
        Args:
            prompt: Il prompt dell'utente
            content: Contenuto da analizzare (opzionale)
            context: Contesto aggiuntivo (opzionale)
        
        Returns:
            list: Lista di messaggi formattati
        """
        message = prompt
        
        if content:
            message += f"\n\nCONTENT TO ANALYZE:\n```\n{content}\n```"
            
        if context:
            message += f"\n\nADDITIONAL CONTEXT:\n{context}"
        
        return [{"role": "user", "content": message}]
    
    def _call_openai(self, messages: list, model: str, max_completion_tokens: Optional[int] = None) -> Generator[str, None, None]:
        """
        Effettua una chiamata streaming ai modelli OpenAI.
        
        Args:
            messages: Lista di messaggi
            model: Nome del modello
            max_completion_tokens: Limite massimo di token per la risposta
            
        Yields:
            str: Chunks della risposta
        """
        try:
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                stream=True,
                max_completion_tokens=max_completion_tokens or 32768
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            st.error(f"Errore OpenAI: {str(e)}")
            yield "Mi dispiace, si è verificato un errore durante l'elaborazione."
    
    def _call_anthropic(self, messages: list) -> Generator[str, None, None]:
        """
        Effettua una chiamata streaming ai modelli Anthropic.
        
        Args:
            messages: Lista di messaggi
            
        Yields:
            str: Chunks della risposta
        """
        try:
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet",
                max_tokens=1024,
                messages=messages,
                stream=True
            )
            
            for chunk in message:
                if chunk.delta.text:
                    yield chunk.delta.text
                    
        except Exception as e:
            st.error(f"Errore Anthropic: {str(e)}")
            yield "Mi dispiace, si è verificato un errore durante l'elaborazione."
    
    def process_request(self, prompt: str, content: Optional[str] = None,
                       context: Optional[str] = None, task_type: Optional[str] = None) -> Generator[str, None, None]:
        """
        Processa una richiesta completa.
        
        Args:
            prompt: Il prompt dell'utente
            content: Contenuto da analizzare (opzionale)
            context: Contesto aggiuntivo (opzionale)
            task_type: Tipo di task per la selezione del modello
            
        Yields:
            str: Chunks della risposta
        """
        # Seleziona il modello appropriato
        model = self.select_model(task_type, len(content)) if task_type and content else st.session_state.current_model
        
        # Prepara i messaggi
        messages = self._prepare_messages(prompt, content, context)
        
        # Effettua la chiamata al modello appropriato
        if model.startswith('o1'):
            yield from self._call_openai(messages, model)
        else:
            yield from self._call_anthropic(messages)
    
    def _calculate_cost(self, model: str, tokens: int) -> float:
        """
        Calcola il costo di una richiesta.
        
        Args:
            model: Nome del modello
            tokens: Numero di token utilizzati
            
        Returns:
            float: Costo in USD
        """
        model_costs = self.cost_map.get(model, {'input': 0, 'output': 0})
        # Stima: 40% input, 60% output
        input_tokens = tokens * 0.4
        output_tokens = tokens * 0.6
        
        cost = (input_tokens * model_costs['input'] + 
                output_tokens * model_costs['output']) / 1000
        return round(cost, 4)