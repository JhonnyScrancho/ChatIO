"""
Test suite for utility functions of Allegro IO Code Assistant.
"""

import pytest
from src.utils.config import load_config
from src.utils.helpers import truncate_text, calculate_tokens, sanitize_input

class TestConfig:
    """Test per le funzionalità di configurazione."""
    
    def test_load_config(self):
        """Test caricamento configurazione."""
        with pytest.raises(ValueError):
            # Test senza variabili d'ambiente necessarie
            load_config()
        
        with pytest.monkeypatch.context() as m:
            # Test con variabili d'ambiente
            m.setenv('OPENAI_API_KEY', 'test_key')
            m.setenv('ANTHROPIC_API_KEY', 'test_key')
            
            config = load_config()
            assert config['OPENAI_API_KEY'] == 'test_key'
            assert config['ANTHROPIC_API_KEY'] == 'test_key'
            assert isinstance(config['MAX_FILE_SIZE'], int)

class TestHelpers:
    """Test per le funzioni helper."""
    
    def test_truncate_text(self):
        """Test truncate text."""
        text = "Hello World!"
        assert truncate_text(text, 5) == "Hello..."
        assert truncate_text(text, 20) == text
        assert truncate_text("", 5) == ""
    
    def test_calculate_tokens(self):
        """Test calcolo tokens."""
        text = "Hello World!"
        assert isinstance(calculate_tokens(text), int)
        assert calculate_tokens("") == 0
    
    def test_sanitize_input(self):
        """Test sanitizzazione input."""
        test_cases = [
            ("Hello<script>alert('test')</script>", "Hello"),
            ("Normal text", "Normal text"),
            ("<h1>Title</h1>", "Title"),
            ("", "")
        ]
        
        for input_text, expected in test_cases:
            assert sanitize_input(input_text) == expected

class TestEnvironment:
    """Test per l'ambiente di esecuzione."""
    
    def test_streamlit_environment(self):
        """Test ambiente Streamlit."""
        import streamlit as st
        assert hasattr(st, 'session_state')
    
    def test_dependencies_installed(self):
        """Test dipendenze installate."""
        import openai
        import anthropic
        import pygments
        assert all([openai, anthropic, pygments])

if __name__ == '__main__':
    pytest.main([__file__])