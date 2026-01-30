"""
DeepL provider
Free tier available with API key
"""
from typing import List, Optional
import os
try:
    from deep_translator import DeepLTranslator
    DEEPL_AVAILABLE = True
except ImportError:
    DEEPL_AVAILABLE = False
    DeepLTranslator = None

from src.translation.base_provider import TranslationProvider
from src.translation.exceptions import (
    TranslationError,
    ProviderUnavailableError,
    TranslationTimeoutError
)


class DeepLProvider(TranslationProvider):
    """DeepL provider (requires API key for free tier)"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize DeepL provider
        
        Args:
            api_key: DeepL API key (from environment or parameter)
        """
        if not DEEPL_AVAILABLE:
            raise ImportError(
                "deep-translator is not installed. Install it with: pip install deep-translator"
            )
        self.api_key = api_key or os.getenv("DEEPL_API_KEY")
        self.translator = None
        
        if self.api_key:
            try:
                self.translator = DeepLTranslator(api_key=self.api_key)
            except Exception:
                pass
    
    @property
    def name(self) -> str:
        return "DeepL"
    
    @property
    def is_available(self) -> bool:
        """Check if DeepL is available (requires API key)"""
        if not DEEPL_AVAILABLE:
            return False
        if not self.api_key:
            return False
        
        if not self.translator:
            return False
        
        try:
            # Test translation
            result = self.translator.translate("test", target="en", source="en")
            return result is not None
        except Exception:
            return False
    
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> str:
        """
        Translate text using DeepL
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (optional)
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        if not self.is_available:
            raise ProviderUnavailableError(
                "DeepL is not available. API key required. "
                "Set DEEPL_API_KEY environment variable."
            )
        
        try:
            result = self.translator.translate(
                text,
                target=target_language,
                source=source_language if source_language else "auto"
            )
            
            if not result:
                raise TranslationError("DeepL returned empty result")
            
            return result
            
        except Exception as e:
            error_str = str(e).lower()
            if "timeout" in error_str or "timed out" in error_str:
                raise TranslationTimeoutError(f"DeepL timeout: {str(e)}")
            elif "api key" in error_str or "authentication" in error_str:
                raise ProviderUnavailableError(f"DeepL authentication error: {str(e)}")
            raise TranslationError(f"DeepL error: {str(e)}")
    
    def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None
    ) -> List[str]:
        """
        Translate multiple texts
        
        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language code (optional)
            
        Returns:
            List of translated texts
        """
        if not texts:
            return []
        
        translated = []
        for text in texts:
            try:
                result = self.translate(text, target_language, source_language)
                translated.append(result)
            except Exception as e:
                # If one translation fails, use original text
                translated.append(text)
                continue
        
        return translated
