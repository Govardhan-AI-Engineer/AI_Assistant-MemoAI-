"""
Google Translate provider using googletrans library or deep-translator fallback
Free, no API key required
"""
from typing import List, Optional
import time
try:
    from googletrans import Translator
    from googletrans.models import Translated
    GOOGLETRANS_AVAILABLE = True
except ImportError:
    GOOGLETRANS_AVAILABLE = False
    Translator = None
    Translated = None

# Fallback to deep-translator's Google Translate
try:
    from deep_translator import GoogleTranslator
    DEEP_TRANSLATOR_GOOGLE_AVAILABLE = True
except ImportError:
    DEEP_TRANSLATOR_GOOGLE_AVAILABLE = False
    GoogleTranslator = None

from src.translation.base_provider import TranslationProvider
from src.translation.exceptions import TranslationError, TranslationTimeoutError


class GoogleTranslateProvider(TranslationProvider):
    """Google Translate provider using googletrans library"""
    
    def __init__(self):
        if not GOOGLETRANS_AVAILABLE and not DEEP_TRANSLATOR_GOOGLE_AVAILABLE:
            raise ImportError(
                "Neither googletrans nor deep-translator is installed. "
                "Install one with: pip install googletrans==4.0.0rc1 OR pip install deep-translator"
            )
        
        # Try googletrans first, fallback to deep-translator
        self.use_googletrans = GOOGLETRANS_AVAILABLE
        if self.use_googletrans:
            try:
                self.translator = Translator()
            except Exception:
                # If googletrans fails to initialize, use deep-translator
                self.use_googletrans = False
        
        if not self.use_googletrans and DEEP_TRANSLATOR_GOOGLE_AVAILABLE:
            self.translator = None  # Will use GoogleTranslator directly
        elif not self.use_googletrans:
            raise ImportError("No Google Translate provider available")
        
        self._last_request_time = 0
        self._min_request_interval = 0.1  # 100ms between requests to avoid rate limiting
    
    @property
    def name(self) -> str:
        return "Google Translate"
    
    @property
    def is_available(self) -> bool:
        """Google Translate is always available (no API key needed)"""
        # Prefer deep-translator if available (more reliable)
        if DEEP_TRANSLATOR_GOOGLE_AVAILABLE:
            try:
                # Quick test with deep-translator
                GoogleTranslator(source='en', target='en').translate("test")
                return True
            except Exception:
                pass
        
        # Fallback to googletrans
        if not self.use_googletrans:
            return False
        
        try:
            # Quick test translation - check if async first
            import inspect
            if inspect.iscoroutinefunction(self.translator.translate):
                # It's async, skip the test (will handle in translate method)
                return True
            else:
                result = self.translator.translate("test", dest="en", src="en")
                return result is not None
        except Exception:
            return False
    
    def _rate_limit(self):
        """Enforce rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)
        self._last_request_time = time.time()
    
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> str:
        """
        Translate text using Google Translate
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (optional)
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        try:
            self._rate_limit()
            
            # Always use deep-translator as primary (more reliable, no async issues)
            if DEEP_TRANSLATOR_GOOGLE_AVAILABLE:
                # Use deep-translator's Google Translate (more reliable, synchronous)
                src = source_language if source_language else None  # None = auto-detect
                try:
                    translated_text = GoogleTranslator(source=src, target=target_language).translate(text)
                    
                    if not translated_text or translated_text.strip() == '':
                        raise TranslationError("Google Translate (deep-translator) returned empty result")
                    
                    # Verify translation actually happened
                    if translated_text.strip() == text.strip():
                        raise TranslationError("Translation returned same text - translation may have failed")
                    
                    return translated_text
                except Exception as e:
                    # If deep-translator fails, try googletrans as fallback
                    if self.use_googletrans:
                        print(f"WARNING: deep-translator failed ({e}), trying googletrans fallback")
                    else:
                        raise TranslationError(f"Translation failed: {e}")
            
            # Fallback to googletrans if deep-translator not available
            if not self.use_googletrans:
                raise TranslationError("No translation provider available")
            
            # Use googletrans (with async handling)
            src = source_language if source_language else 'auto'
            
            # Check if translate is a coroutine
            import inspect
            translate_method = self.translator.translate
            is_async = inspect.iscoroutinefunction(translate_method)
            
            if is_async:
                # Handle async - use asyncio
                import asyncio
                try:
                    # Try to get existing event loop
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            # Loop is running, need nest_asyncio
                            try:
                                import nest_asyncio
                                nest_asyncio.apply()
                            except ImportError:
                                raise TranslationError(
                                    "googletrans is async and event loop is running. "
                                    "Install nest-asyncio: pip install nest-asyncio"
                                )
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                    
                    # Run the coroutine
                    result = loop.run_until_complete(translate_method(text, dest=target_language, src=src))
                except Exception as e:
                    raise TranslationError(f"Async translation failed: {e}")
            else:
                # Synchronous call
                result: Translated = translate_method(
                    text,
                    dest=target_language,
                    src=src
                )
            
            if not result:
                raise TranslationError("Google Translate returned None")
            
            # Handle both dict and object responses
            if isinstance(result, dict):
                translated_text = result.get('text', '') or result.get('translatedText', '')
            else:
                translated_text = result.text if hasattr(result, 'text') else str(result)
            
            if not translated_text or translated_text.strip() == '':
                raise TranslationError("Google Translate returned empty result")
            
            # Verify translation actually happened (not same as source)
            if translated_text.strip() == text.strip():
                raise TranslationError(f"Translation returned same text - translation may have failed")
            
            return translated_text
            
        except TranslationError:
            raise  # Re-raise our custom errors
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                raise TranslationTimeoutError(f"Google Translate timeout: {error_msg}")
            if "coroutine" in error_msg.lower():
                raise TranslationError(f"Google Translate async error: {error_msg}. Try installing: pip install nest-asyncio")
            raise TranslationError(f"Google Translate error: {error_msg}")
    
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
