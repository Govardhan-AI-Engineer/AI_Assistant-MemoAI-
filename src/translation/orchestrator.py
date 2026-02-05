"""
Translation orchestrator with fallback mechanism and quality refinement
"""
from typing import List, Optional, Dict, Tuple
from src.translation.base_provider import TranslationProvider, TranslationGranularity
from src.translation.exceptions import (
    TranslationError,
    ProviderUnavailableError,
    TranslationTimeoutError
)
# Lazy imports to handle missing dependencies gracefully
try:
    from src.translation.google_provider import GoogleTranslateProvider
except ImportError:
    GoogleTranslateProvider = None

try:
    from src.translation.libre_provider import LibreTranslateProvider
except ImportError:
    LibreTranslateProvider = None

try:
    from src.translation.deepl_provider import DeepLProvider
except ImportError:
    DeepLProvider = None

try:
    from src.translation.ai_provider import AITranslationProvider
except ImportError:
    AITranslationProvider = None


class TranslationOrchestrator:
    """
    Orchestrates translation across multiple providers with fallback
    """
    
    def __init__(
        self,
        provider_priority: Optional[List[str]] = None,
        enable_retranslation: bool = True
    ):
        """
        Initialize translation orchestrator
        
        Args:
            provider_priority: List of provider names in priority order
                             Options: 'google', 'libre', 'deepl', 'ai'
                             Default: ['google', 'libre', 'deepl', 'ai']
            enable_retranslation: Enable re-translation for quality refinement
        """
        # Initialize all providers (only if available)
        self.providers: Dict[str, TranslationProvider] = {}
        
        if GoogleTranslateProvider is not None:
            try:
                self.providers['google'] = GoogleTranslateProvider()
            except Exception:
                pass
        
        if LibreTranslateProvider is not None:
            try:
                self.providers['libre'] = LibreTranslateProvider()
            except Exception:
                pass
        
        if DeepLProvider is not None:
            try:
                self.providers['deepl'] = DeepLProvider()
            except Exception:
                pass
        
        if AITranslationProvider is not None:
            try:
                self.providers['ai'] = AITranslationProvider()
            except Exception:
                pass
        
        # Set provider priority (default: google -> libre -> deepl -> ai)
        self.provider_priority = provider_priority or ['google', 'libre', 'deepl', 'ai']
        
        # Filter to only available providers
        self.available_providers = [
            name for name in self.provider_priority
            if name in self.providers and self.providers[name].is_available
        ]
        
        if not self.available_providers:
            # Provide helpful error message with installation instructions
            missing_deps = []
            if GoogleTranslateProvider is None:
                missing_deps.append("googletrans==4.0.0rc1")
            if DeepLProvider is None:
                missing_deps.append("deep-translator>=1.11.4")
            
            error_msg = (
                "No translation providers are available.\n\n"
                "Please check:\n"
                "1. Install required dependencies:\n"
            )
            if missing_deps:
                error_msg += f"   pip install {' '.join(missing_deps)}\n"
            error_msg += (
                "2. For DeepL: Set DEEPL_API_KEY in environment (optional)\n"
                "3. For LibreTranslate: Configure LIBRETRANSLATE_API_URL (optional)\n\n"
                "At least one provider must be available for translation to work."
            )
            raise TranslationError(error_msg)
        
        self.enable_retranslation = enable_retranslation
    
    def _get_provider(self, provider_name: str) -> Optional[TranslationProvider]:
        """Get provider by name"""
        return self.providers.get(provider_name)
    
    def translate_with_fallback(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> Tuple[str, str, bool, Optional[str]]:
        """
        Translate text with automatic fallback
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (optional)
            preferred_provider: Preferred provider name (optional)
            
        Returns:
            Tuple of (translated_text, provider_name, used_preferred, fallback_provider)
            - translated_text: Translated text
            - provider_name: Name of provider that succeeded
            - used_preferred: True if preferred provider was used, False if fallback occurred
            - fallback_provider: Name of provider used if fallback occurred (None if preferred was used)
            
        Raises:
            TranslationError: If all providers fail
        """
        if not text or not text.strip():
            return text, "none", False, None
        
        # Language-specific provider preference
        # For Telugu to any language, prefer AI translation (Groq) as it works better
        if not preferred_provider:
            if source_language == 'te':
                preferred_provider = 'ai'
        
        # Start with preferred provider if specified and available
        providers_to_try = []
        preferred_was_available = False
        if preferred_provider and preferred_provider in self.available_providers:
            providers_to_try.append(preferred_provider)
            preferred_was_available = True
        
        # Add remaining available providers
        for provider_name in self.available_providers:
            if provider_name not in providers_to_try:
                providers_to_try.append(provider_name)
        
        # Try each provider in order
        last_error = None
        preferred_failed = False
        for idx, provider_name in enumerate(providers_to_try):
            provider = self._get_provider(provider_name)
            if not provider or not provider.is_available:
                continue
            
            try:
                translated = provider.translate(text, target_language, source_language)
                
                # Check if result is a coroutine (async issue)
                import inspect
                if inspect.iscoroutine(translated):
                    print(f"WARNING: {provider_name} returned coroutine, skipping...")
                    last_error = TranslationError(f"{provider_name} returned coroutine (async issue)")
                    if provider_name == preferred_provider:
                        preferred_failed = True
                    continue
                
                # Validate output
                if provider.validate_output(translated):
                    # Check if this was the preferred provider
                    used_preferred = (provider_name == preferred_provider and preferred_was_available)
                    fallback_provider = None if used_preferred else provider_name
                    return translated, provider_name, used_preferred, fallback_provider
                else:
                    # Output is invalid, try next provider
                    last_error = TranslationError(
                        f"{provider_name} returned invalid output"
                    )
                    if provider_name == preferred_provider:
                        preferred_failed = True
                    continue
                    
            except (ProviderUnavailableError, TranslationTimeoutError) as e:
                # Provider unavailable or timeout - try next
                last_error = e
                if provider_name == preferred_provider:
                    preferred_failed = True
                continue
            except TranslationError as e:
                # Other translation error - try next
                last_error = e
                if provider_name == preferred_provider:
                    preferred_failed = True
                continue
            except Exception as e:
                # Unexpected error - try next
                last_error = TranslationError(f"Unexpected error with {provider_name}: {str(e)}")
                if provider_name == preferred_provider:
                    preferred_failed = True
                continue
        
        # All providers failed
        raise TranslationError(
            f"All translation providers failed. Last error: {str(last_error)}"
        )
    
    def translate_batch_with_fallback(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> Tuple[List[str], str]:
        """
        Translate multiple texts with fallback
        
        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language code (optional)
            preferred_provider: Preferred provider name (optional)
            
        Returns:
            Tuple of (translated_texts, provider_name)
        """
        if not texts:
            return [], "none"
        
        # Try to use preferred provider for all texts
        if preferred_provider and preferred_provider in self.available_providers:
            provider = self._get_provider(preferred_provider)
            if provider and provider.is_available:
                try:
                    translated = provider.translate_batch(texts, target_language, source_language)
                    # Validate all outputs
                    if all(provider.validate_output(t) for t in translated):
                        return translated, preferred_provider
                except Exception:
                    pass  # Fall through to individual translation
        
        # Translate individually with fallback
        translated = []
        provider_used = None
        for text in texts:
            try:
                result, provider_name = self.translate_with_fallback(
                    text,
                    target_language,
                    source_language,
                    preferred_provider
                )
                translated.append(result)
                if not provider_used:
                    provider_used = provider_name
            except Exception:
                # If translation fails, use original text
                translated.append(text)
        
        return translated, provider_used or "mixed"
    
    def retranslate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        primary_provider: Optional[str] = None,
        secondary_provider: Optional[str] = None
    ) -> Tuple[str, str, Optional[str]]:
        """
        Re-translate text using secondary provider for quality refinement
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (optional)
            primary_provider: Primary provider name (optional)
            secondary_provider: Secondary provider name (optional)
            
        Returns:
            Tuple of (translated_text, primary_provider, secondary_provider)
        """
        if not self.enable_retranslation:
            # Re-translation disabled, use normal translation
            translated, provider = self.translate_with_fallback(
                text, target_language, source_language, primary_provider
            )
            return translated, provider, None
        
        # First translation with primary provider
        primary_translated, primary_name = self.translate_with_fallback(
            text,
            target_language,
            source_language,
            primary_provider
        )
        
        # If secondary provider specified and different from primary, re-translate
        if secondary_provider and secondary_provider != primary_name:
            secondary = self._get_provider(secondary_provider)
            if secondary and secondary.is_available:
                try:
                    # Re-translate the already-translated text
                    # This can help refine quality
                    secondary_translated = secondary.translate(
                        primary_translated,
                        target_language,
                        target_language  # Source is now target (refinement)
                    )
                    
                    if secondary.validate_output(secondary_translated):
                        return secondary_translated, primary_name, secondary_provider
                except Exception:
                    # Re-translation failed, use primary result
                    pass
        
        return primary_translated, primary_name, None
