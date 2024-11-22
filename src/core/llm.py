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
    
    def prepare_prompt(self, prompt: str, analysis_type: Optional[str] = None,
                      file_content: Optional[str] = None, context: Optional[str] = None) -> str:
        """
        Prepara il prompt completo.
        
        Args:
            prompt: Il prompt base dell'utente
            analysis_type: Tipo di analisi richiesta
            file_content: Contenuto del file da analizzare
            context: Contesto aggiuntivo
            
        Returns:
            str: Prompt completo formattato
        """
        # Aggiungi il template di sistema se specificato
        final_prompt = self.system_templates.get(analysis_type, "") + "\n\n" if analysis_type else ""
        
        # Aggiungi il prompt base
        final_prompt += prompt
        
        # Aggiungi il contenuto del file se presente
        if file_content:
            final_prompt += f"\n\nFile content:\n```\n{file_content}\n```"
            
        # Aggiungi il contesto se presente
        if context:
            final_prompt += f"\n\nAdditional context:\n{context}"
            
        return final_prompt
    
    def _call_openai(self, prompt: str, model: str) -> Generator[str, None, None]:
        """
        Effettua una chiamata streaming ai modelli OpenAI.
        
        Args:
            prompt: Prompt completo
            model: Nome del modello
            
        Yields:
            str: Chunks della risposta
        """
        try:
            completion = self.openai_client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                max_completion_tokens=32768
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
            prompt: Prompt completo
            
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
    
    def process_request(self, prompt: str, analysis_type: Optional[str] = None,
                       file_content: Optional[str] = None, context: Optional[str] = None) -> Generator[str, None, None]:
        """
        Processa una richiesta completa.
        
        Args:
            prompt: Il prompt dell'utente
            analysis_type: Tipo di analisi richiesta
            file_content: Contenuto del file da analizzare
            context: Contesto aggiuntivo
            
        Yields:
            str: Chunks della risposta
        """
        # Prepara il prompt completo
        final_prompt = self.prepare_prompt(prompt, analysis_type, file_content, context)
        
        # Seleziona il modello appropriato
        if analysis_type and file_content:
            model = self.select_model(analysis_type, len(file_content))
        else:
            model = st.session_state.current_model
        
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
        # Stima: 40% input, 60% output
        input_tokens = tokens * 0.4
        output_tokens = tokens * 0.6
        
        cost = (input_tokens * model_costs['input'] + 
                output_tokens * model_costs['output']) / 1000
        return round(cost, 4)