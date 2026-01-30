"""
LibreTranslate provider
Open-source, self-hosted or public API
"""
from typing import List, Optional
import requests
import os
from src.translation.base_provider import TranslationProvider
from src.translation.exceptions import (
    TranslationError,
    ProviderUnavailableError,
    TranslationTimeoutError
)


class LibreTranslateProvider(TranslationProvider):
    """LibreTranslate provider (open-source translation API)"""
    
    # Default public API endpoint (can be overridden)
    DEFAULT_API_URL = "https://libretranslate.com/translate"
    
    def __init__(self, api_url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize LibreTranslate provider
        
        Args:
            api_url: LibreTranslate API URL (default: public API)
            api_key: API key if required (from environment or parameter)
        """
        self.api_url = api_url or os.getenv("LIBRETRANSLATE_API_URL", self.DEFAULT_API_URL)
        self.api_key = api_key or os.getenv("LIBRETRANSLATE_API_KEY")
        self.timeout = 30  # seconds
    
    @property
    def name(self) -> str:
        return "LibreTranslate"
    
    @property
    def is_available(self) -> bool:
        """Check if LibreTranslate is available"""
        try:
            # Test API availability - try languages endpoint
            languages_url = self.api_url.replace("/translate", "/languages")
            if languages_url == self.api_url:
                # If replace didn't work, construct languages URL
                languages_url = self.api_url.rsplit("/", 1)[0] + "/languages"
            
            response = requests.get(languages_url, timeout=5)
            return response.status_code == 200
        except Exception:
            # If languages endpoint fails, assume available (will fail on actual use)
            # This allows the provider to be used even if languages endpoint is unavailable
            return True
    
    def _make_request(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> str:
        """
        Make translation request to LibreTranslate API
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (optional)
            
        Returns:
            Translated text
        """
        payload = {
            "q": text,
            "target": target_language,
            "format": "text"
        }
        
        if source_language:
            payload["source"] = source_language
        
        if self.api_key:
            payload["api_key"] = self.api_key
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            translated_text = result.get("translatedText", "")
            
            if not translated_text:
                raise TranslationError("LibreTranslate returned empty result")
            
            return translated_text
            
        except requests.Timeout:
            raise TranslationTimeoutError("LibreTranslate request timed out")
        except requests.RequestException as e:
            raise TranslationError(f"LibreTranslate API error: {str(e)}")
        except Exception as e:
            raise TranslationError(f"LibreTranslate error: {str(e)}")
    
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> str:
        """
        Translate text using LibreTranslate
        
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
            raise ProviderUnavailableError("LibreTranslate is not available")
        
        return self._make_request(text, target_language, source_language)
    
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
