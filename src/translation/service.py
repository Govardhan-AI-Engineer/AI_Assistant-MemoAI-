"""
Main translation service with paragraph-level and line-by-line support
"""
from typing import List, Optional, Dict, Tuple
from src.translation.base_provider import TranslationGranularity
from src.translation.orchestrator import TranslationOrchestrator
from src.translation.exceptions import TranslationError


class TranslationService:
    """
    Main translation service with granularity control
    """
    
    def __init__(
        self,
        provider_priority: Optional[List[str]] = None,
        enable_retranslation: bool = True
    ):
        """
        Initialize translation service
        
        Args:
            provider_priority: Provider priority order (default: ['google', 'libre', 'deepl'])
            enable_retranslation: Enable re-translation for quality refinement
        """
        self.orchestrator = TranslationOrchestrator(
            provider_priority=provider_priority,
            enable_retranslation=enable_retranslation
        )
    
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        granularity: TranslationGranularity = TranslationGranularity.PARAGRAPH,
        preferred_provider: Optional[str] = None,
        enable_retranslation: Optional[bool] = None
    ) -> Dict:
        """
        Translate text with specified granularity
        
        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'en', 'es', 'hi')
            source_language: Source language code (optional, auto-detect if None)
            granularity: Translation granularity (WHOLE_TEXT, PARAGRAPH, or LINE_BY_LINE)
            preferred_provider: Preferred provider name (optional)
            enable_retranslation: Override global retranslation setting (optional)
            
        Returns:
            Dictionary with:
            - 'text': Translated text
            - 'provider': Provider name used
            - 'secondary_provider': Secondary provider if re-translation used
            - 'granularity': Granularity used
        """
        if not text or not text.strip():
            return {
                'text': text,
                'provider': 'none',
                'secondary_provider': None,
                'granularity': granularity.value
            }
        
        # Track fallback information
        used_preferred_provider = True
        fallback_provider_used = None
        
        # Split text based on granularity
        if granularity == TranslationGranularity.WHOLE_TEXT:
            # Translate entire text as one unit - best for context preservation
            # This ensures all words are translated, especially when source language is known
            if source_language:
                # Source language known - translate as one unit for maximum context
                translated_text, provider, used_pref, fallback_prov = self.orchestrator.translate_with_fallback(
                    text,
                    target_language,
                    source_language,
                    preferred_provider
                )
            else:
                # Source language unknown - still translate as one unit but with auto-detect
                translated_text, provider, used_pref, fallback_prov = self.orchestrator.translate_with_fallback(
                    text,
                    target_language,
                    None,  # Auto-detect
                    preferred_provider
                )
            used_preferred_provider = used_pref
            fallback_provider_used = fallback_prov
        elif granularity == TranslationGranularity.LINE_BY_LINE:
            # Line-by-line translation (useful for subtitles)
            lines = self._split_into_lines(text)
            translated_lines, provider = self.orchestrator.translate_batch_with_fallback(
                lines,
                target_language,
                source_language,
                preferred_provider
            )
            translated_text = '\n'.join(translated_lines)
            # For batch, check if preferred was used (simplified check)
            used_preferred_provider = (provider == preferred_provider) if preferred_provider else True
            fallback_provider_used = None if used_preferred_provider else provider
        else:
            # Paragraph-level: translate paragraph by paragraph
            paragraphs = self._split_into_paragraphs(text)
            translated_paragraphs, provider = self.orchestrator.translate_batch_with_fallback(
                paragraphs,
                target_language,
                source_language,
                preferred_provider
            )
            translated_text = '\n\n'.join(translated_paragraphs)
            # For batch, check if preferred was used (simplified check)
            used_preferred_provider = (provider == preferred_provider) if preferred_provider else True
            fallback_provider_used = None if used_preferred_provider else provider
        
        # Optional re-translation for quality refinement
        # This is especially important for paragraph-level translation
        secondary_provider = None
        should_retranslate = enable_retranslation if enable_retranslation is not None else self.orchestrator.enable_retranslation
        
        if should_retranslate:
            try:
                # For paragraph-level, re-translate each paragraph individually for better quality
                if granularity == TranslationGranularity.PARAGRAPH:
                    # Re-translate each paragraph with secondary provider for refinement
                    paragraphs = self._split_into_paragraphs(text)
                    retranslated_paragraphs = []
                    secondary_prov = None
                    
                    # Split the already-translated text back into paragraphs for comparison
                    translated_para_list = translated_text.split('\n\n')
                    
                    for idx, para in enumerate(paragraphs):
                        try:
                            retranslated_para, primary_prov, sec_prov = self.orchestrator.retranslate(
                                para,
                                target_language,
                                source_language,
                                preferred_provider,
                                self._get_secondary_provider(preferred_provider)
                            )
                            retranslated_paragraphs.append(retranslated_para)
                            if sec_prov and not secondary_prov:
                                secondary_prov = sec_prov
                        except Exception:
                            # If re-translation fails for a paragraph, use original translation
                            if idx < len(translated_para_list):
                                retranslated_paragraphs.append(translated_para_list[idx])
                            else:
                                # Fallback: use original paragraph (shouldn't happen, but safe)
                                retranslated_paragraphs.append(para)
                    
                    if retranslated_paragraphs:
                        translated_text = '\n\n'.join(retranslated_paragraphs)
                        secondary_provider = secondary_prov
                else:
                    # For WHOLE_TEXT or LINE_BY_LINE, re-translate the entire result
                    translated_text, primary_prov, secondary_prov = self.orchestrator.retranslate(
                        text,
                        target_language,
                        source_language,
                        preferred_provider,
                        self._get_secondary_provider(preferred_provider)
                    )
                    secondary_provider = secondary_prov
            except Exception as e:
                # Re-translation failed, use primary result
                print(f"Warning: Re-translation failed: {e}")
                pass
        
        return {
            'text': translated_text,
            'provider': provider,
            'secondary_provider': secondary_provider,
            'granularity': granularity.value,
            'source_language': source_language,
            'target_language': target_language,
            'used_preferred_provider': used_preferred_provider,
            'fallback_provider': fallback_provider_used
        }
    
    def translate_paragraphs(
        self,
        paragraphs: List[str],
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> List[str]:
        """
        Translate list of paragraphs
        
        Args:
            paragraphs: List of paragraph texts
            target_language: Target language code
            source_language: Source language code (optional)
            preferred_provider: Preferred provider name (optional)
            
        Returns:
            List of translated paragraphs
        """
        translated, _ = self.orchestrator.translate_batch_with_fallback(
            paragraphs,
            target_language,
            source_language,
            preferred_provider
        )
        return translated
    
    def translate_lines(
        self,
        lines: List[str],
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> List[str]:
        """
        Translate list of lines (for subtitles)
        
        Args:
            lines: List of line texts
            target_language: Target language code
            source_language: Source language code (optional)
            preferred_provider: Preferred provider name (optional)
            
        Returns:
            List of translated lines
        """
        translated, _ = self.orchestrator.translate_batch_with_fallback(
            lines,
            target_language,
            source_language,
            preferred_provider
        )
        return translated
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs"""
        if not text:
            return []
        
        # Split by double newlines or single newline if followed by capital letter
        paragraphs = []
        current_paragraph = []
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                if current_paragraph:
                    paragraphs.append(' '.join(current_paragraph))
                    current_paragraph = []
            else:
                current_paragraph.append(line)
        
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        return paragraphs if paragraphs else [text]
    
    def _split_into_lines(self, text: str) -> List[str]:
        """Split text into lines"""
        if not text:
            return []
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return lines if lines else [text]
    
    def _get_secondary_provider(self, primary_provider: Optional[str]) -> Optional[str]:
        """Get secondary provider for re-translation"""
        available = self.orchestrator.available_providers
        
        if not primary_provider or primary_provider not in available:
            # No primary, use second available
            return available[1] if len(available) > 1 else None
        
        # Find next provider after primary
        try:
            primary_idx = available.index(primary_provider)
            if primary_idx + 1 < len(available):
                return available[primary_idx + 1]
        except ValueError:
            pass
        
        # Fallback: use first different provider
        for provider in available:
            if provider != primary_provider:
                return provider
        
        return None
    
    def get_available_providers(self) -> List[str]:
        """Get list of available providers"""
        return self.orchestrator.available_providers.copy()
    
    def get_provider_info(self) -> Dict[str, Dict]:
        """Get information about all providers"""
        info = {}
        for name, provider in self.orchestrator.providers.items():
            info[name] = {
                'name': provider.name,
                'available': provider.is_available,
                'priority': name in self.orchestrator.available_providers
            }
        return info
