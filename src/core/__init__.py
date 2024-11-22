"""
Core package for Allegro IO Code Assistant.
Contains main functionality for session management, LLM integration, and file processing.
"""

from .session import SessionManager
from .llm import LLMManager
from .files import FileManager

__all__ = ['SessionManager', 'LLMManager', 'FileManager']