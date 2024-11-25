"""
UI package for Allegro IO Code Assistant.
Contains layout and components for the Streamlit interface.
"""

from .layout import render_app_layout
from .components import FileExplorer, ChatInterface, CodeViewer, ModelSelector, StatsDisplay

__all__ = [
    'render_app_layout',
    'FileExplorer',
    'ChatInterface',
    'CodeViewer',
    'ModelSelector',
    'StatsDisplay'
]