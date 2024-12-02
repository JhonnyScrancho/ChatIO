# src/ui/__init__.py
"""
UI package for Allegro IO Code Assistant.
Contains components for the Streamlit interface.
"""

__all__ = [
    'FileExplorer',
    'ChatInterface',
    'CodeViewer',
    'ModelSelector',
    'StatsDisplay'
]

# Sposta l'import dopo __all__
from .components import FileExplorer, ChatInterface, CodeViewer, ModelSelector, StatsDisplay