"""
Base provider interface for translation services
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict
from enum import Enum


class TranslationGranularity(Enum):
    """Translation granularity options"""
    WHOLE_TEXT = "whole_text"  # Translate entire text as one unit (best for context preservation)
    PARAGRAPH = "paragraph"  # Translate paragraph by paragraph
    LINE_BY_LINE = "line_by_line"  # Translate line by line (for subtitles)


class TranslationProvider(ABC):
    """Base class for translation providers"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name"""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider is available (API key, service up, etc.)"""
        pass
    
    @abstractmethod
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> str:
        """
        Translate text to target language
        
        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'en', 'es', 'hi')
            source_language: Source language code (optional, auto-detect if None)
            
        Returns:
            Translated text
            
        Raises:
            TranslationError: If translation fails
        """
        pass
    
    @abstractmethod
    def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None
    ) -> List[str]:
        """
        Translate multiple texts (for batch processing)
        
        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language code (optional)
            
        Returns:
            List of translated texts
            
        Raises:
            TranslationError: If translation fails
        """
        pass
    
    def validate_output(self, translated_text: str) -> bool:
        """
        Validate translation output quality
        
        Args:
            translated_text: Translated text to validate
            
        Returns:
            True if output is valid, False otherwise
        """
        if not translated_text or not translated_text.strip():
            return False
        
        # Check for obvious errors (all same character, too short, etc.)
        if len(translated_text.strip()) < 2:
            return False
        
        # Check for corrupted output (all special characters)
        if all(not c.isalnum() and c not in ' .,!?;:' for c in translated_text):
            return False
        
        return True
