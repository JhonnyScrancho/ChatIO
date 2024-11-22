"""
LLM integration for Allegro IO Code Assistant.
Manages interactions with OpenAI and Anthropic models.
"""

import os
from typing import Dict, Optional, Tuple
from openai import OpenAI
from anthropic import Anthropic
from .session import SessionManager

class LLMManager:
    """Gestisce le interazioni con i modelli LLM."""
    
    def __init__(self):
        """Inizializza le connessioni API."""
        self.openai_client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
        self.anthropic_client = Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        self.session = SessionManager()
        
        # Costi per 1K tokens (in USD)
        self.cost_map = {
            'o1-preview': {'input': 0.01, 'output': 0.03},
            'o1-mini': {'input': 0.001, 'output': 0.002},
            'claude-3-5-sonnet': {'input': 0.008, 'output': 0.024}
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
            return "claude-3-5-sonnet"
        elif task_type in ["architecture", "review"]:
            return "o1-preview"
        else:
            return "o1-mini"
    
    def get_template(self, template_name: str) -> str:
        """Carica un template di prompt."""
        template_path = f"templates/{template_name}.txt"
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return ""
    
    def prepare_prompt(self, template_name: str, **kwargs) -> str:
        """Prepara il prompt combinando template e variabili."""
        template = self.get_template(template_name)
        return template.format(**kwargs) if template else kwargs.get('prompt', '')
    
    def _call_openai(self, prompt: str, model: str) -> Tuple[str, int]:
        """Effettua una chiamata ai modelli OpenAI."""
        completion = self.openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        response_chunks = []
        total_tokens = 0
        
        for chunk in completion:
            if chunk.choices[0].delta.content:
                response_chunks.append(chunk.choices[0].delta.content)
                yield chunk.choices[0].delta.content, total_tokens
            if chunk.usage:
                total_tokens = chunk.usage.total_tokens
    
    def _call_anthropic(self, prompt: str) -> Tuple[str, int]:
        """Effettua una chiamata ai modelli Anthropic."""
        message = self.anthropic_client.messages.create(
            model="claude-3-5-sonnet",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
            stream=True
        )
        
        response_chunks = []
        total_tokens = 0
        
        for chunk in message:
            if chunk.delta.text:
                response_chunks.append(chunk.delta.text)
                yield chunk.delta.text, total_tokens
            if chunk.usage:
                total_tokens = chunk.usage.total_tokens
    
    def process_request(self, prompt: str, template_name: Optional[str] = None, 
                       task_type: Optional[str] = None, code_size: Optional[int] = 0) -> Dict:
        """
        Processa una richiesta LLM completa.
        
        Args:
            prompt: Il prompt dell'utente
            template_name: Nome del template da utilizzare (opzionale)
            task_type: Tipo di task per la selezione del modello
            code_size: Dimensione del codice per la selezione del modello
            
        Returns:
            Dict: Risultato della richiesta con tokens e costo
        """
        # Seleziona o usa il modello corrente
        if task_type and code_size:
            model = self.select_model(task_type, code_size)
            self.session.set_current_model(model)
        else:
            model = self.session.get_current_model()
        
        # Prepara il prompt finale
        final_prompt = self.prepare_prompt(template_name, prompt=prompt) if template_name else prompt
        
        # Effettua la chiamata al modello appropriato
        if model.startswith('o1'):
            response_generator = self._call_openai(final_prompt, model)
        else:
            response_generator = self._call_anthropic(final_prompt)
        
        # Processa la risposta
        response_chunks = []
        total_tokens = 0
        
        for chunk, tokens in response_generator:
            response_chunks.append(chunk)
            total_tokens = tokens
            yield chunk
        
        # Calcola e aggiorna i costi
        cost = self._calculate_cost(model, total_tokens)
        self.session.update_token_count(total_tokens)
        self.session.update_cost(cost)
    
    def _calculate_cost(self, model: str, tokens: int) -> float:
        """Calcola il costo di una richiesta."""
        model_costs = self.cost_map.get(model, {'input': 0, 'output': 0})
        # Semplificazione: consideriamo il 40% input e 60% output
        input_tokens = tokens * 0.4
        output_tokens = tokens * 0.6
        
        cost = (input_tokens * model_costs['input'] + 
                output_tokens * model_costs['output']) / 1000
        return round(cost, 4)