"""
LLM integration for Allegro IO Code Assistant.
Manages interactions with OpenAI and Anthropic models.
"""

import streamlit as st
from typing import Dict, Optional, Tuple, Generator
from openai import OpenAI
from anthropic import Anthropic
import json

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
        
        # Template di sistema per diversi tipi di analisi
        self.system_templates = {
            'code_review': """You are a senior software engineer performing a code review. 
                            Focus on: code quality, patterns, potential issues, and suggestions for improvement.""",
            'architecture': """You are a software architect analyzing code structure. 
                            Focus on: architectural patterns, SOLID principles, and scalability concerns.""",
            'security': """You are a security expert reviewing code for vulnerabilities. 
                         Focus on: security issues, best practices, and potential risks.""",
            'performance': """You are a performance optimization expert. 
                            Focus on: performance bottlenecks, optimization opportunities, and efficiency improvements."""
        }
    
    def select_model(self, task_type: str, code_size: int) -> str:
        """
        Seleziona automaticamente il modello più appropriato.
        
        Args:
            task_type: Tipo di task (es. 'architecture', 'review', 'debug')
            code_size: Dimensione del codice in bytes
            
        Returns:
            str: Nome del modello selezionato
        """
        if code_size > 100_000:
            return "claude-3-5-sonnet"  # Per file grandi
        elif task_type in ["architecture", "review", "security"]:
            return "o1-preview"  # Per analisi complesse
        else:
            return "o1-mini"  # Per task semplici
    
    def prepare_prompt(self, task_type: str, code: str, context: Optional[str] = None) -> str:
        """
        Prepara il prompt per il modello.
        
        Args:
            task_type: Tipo di analisi richiesta
            code: Codice da analizzare
            context: Contesto aggiuntivo (opzionale)
            
        Returns:
            str: Prompt formattato
        """
        system_prompt = self.system_templates.get(task_type, "You are a helpful code assistant.")
        
        prompt = f"{system_prompt}\n\nCODE TO ANALYZE:\n```\n{code}\n```\n"
        
        if context:
            prompt += f"\nADDITIONAL CONTEXT:\n{context}\n"
            
        prompt += "\nPlease provide your analysis:"
        
        return prompt
    
    def _call_openai(self, prompt: str, model: str) -> Generator[str, None, None]:
        """
        Effettua una chiamata streaming ai modelli OpenAI.
        
        Args:
            prompt: Prompt da inviare
            model: Nome del modello
            
        Yields:
            str: Chunks della risposta
        """
        try:
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            st.error(f"Errore OpenAI: {str(e)}")
            yield "Mi dispiace, si è verificato un errore durante l'elaborazione."
    
    def _call_anthropic(self, prompt: str) -> Generator[str, None, None]:
        """
        Effettua una chiamata streaming ai modelli Anthropic.
        
        Args:
            prompt: Prompt da inviare
            
        Yields:
            str: Chunks della risposta
        """
        try:
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            
            for chunk in message:
                if chunk.delta.text:
                    yield chunk.delta.text
                    
        except Exception as e:
            st.error(f"Errore Anthropic: {str(e)}")
            yield "Mi dispiace, si è verificato un errore durante l'elaborazione."
    
    def process_request(self, prompt: str, task_type: Optional[str] = None,
                       code: Optional[str] = None, context: Optional[str] = None) -> Generator[str, None, None]:
        """
        Processa una richiesta completa.
        
        Args:
            prompt: Prompt dell'utente
            task_type: Tipo di task (opzionale)
            code: Codice da analizzare (opzionale)
            context: Contesto aggiuntivo (opzionale)
            
        Yields:
            str: Chunks della risposta
        """
        # Prepara il prompt completo se necessario
        final_prompt = self.prepare_prompt(task_type, code, context) if code else prompt
        
        # Seleziona il modello appropriato
        if task_type and code:
            model = self.select_model(task_type, len(code))
        else:
            model = st.session_state.get('current_model', 'o1-mini')
        
        # Effettua la chiamata al modello appropriato
        if model.startswith('o1'):
            yield from self._call_openai(final_prompt, model)
        else:
            yield from self._call_anthropic(final_prompt)
    
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
        # Semplificazione: consideriamo il 40% input e 60% output
        input_tokens = tokens * 0.4
        output_tokens = tokens * 0.6
        
        cost = (input_tokens * model_costs['input'] + 
                output_tokens * model_costs['output']) / 1000
        return round(cost, 4)