"""
Robust integration layer for translation with transcription results
Uses RobustTranslator for code-mixed multilingual speech
"""
from typing import Dict, Optional, List, Any
from src.translation.robust_translator import RobustTranslator
from src.translation.exceptions import TranslationError


class RobustTranscriptionTranslationIntegration:
    """
    Robust integration layer for translation with transcription results
    Designed for code-mixed multilingual speech (Hinglish, etc.)
    """
    
    def __init__(
        self,
        provider_priority: Optional[list] = None,
        enable_normalization: bool = True,
        enable_llm_refinement: bool = False,
        llm_model: Optional[str] = None
    ):
        """
        Initialize robust translation integration
        
        Args:
            provider_priority: Provider priority order (default from config)
            enable_normalization: Enable text normalization before translation
            enable_llm_refinement: Enable LLM-based refinement (requires free/open-source LLM)
            llm_model: LLM model name for refinement
            
        Raises:
            TranslationError: If RobustTranslator cannot be initialized
        """
        try:
            self.robust_translator = RobustTranslator(
                provider_priority=provider_priority,
                enable_normalization=enable_normalization,
                enable_llm_refinement=enable_llm_refinement,
                llm_model=llm_model
            )
        except Exception as e:
            raise TranslationError(
                f"Failed to initialize robust translation service: {str(e)}\n"
                "Please ensure all required dependencies are installed."
            ) from e
    
    def translate_transcription(
        self,
        transcription_result: Dict,
        target_language: str,
        preferred_provider: Optional[str] = None,
        use_sentence_by_sentence: bool = True,
        use_two_step: bool = False,
        enable_paragraph_retranslation: bool = False
    ) -> Dict:
        """
        Translate transcription result using robust pipeline
        
        Args:
            transcription_result: Transcription result dictionary with 'text' and 'language'
            target_language: Target language code
            preferred_provider: Preferred provider name
            use_sentence_by_sentence: Translate sentence-by-sentence (recommended)
            use_two_step: Use two-step translation (normalize first, then translate)
            
        Returns:
            Dictionary with original and translated text, plus metadata
        """
        source_text = transcription_result.get('text', '')
        source_language = transcription_result.get('language')
        
        if not source_text:
            return {
                'original_text': source_text,
                'translated_text': source_text,
                'source_language': source_language,
                'target_language': target_language,
                'translation': {}
            }
        
        # Source language must be provided
        if not source_language:
            raise TranslationError(
                "Source language is required for robust translation. "
                "Transcription result must include 'language' field."
            )
        
        # Language-specific provider preference
        # For Telugu to any language, prefer AI translation (Groq) as it works better
        if not preferred_provider and source_language == 'te':
            preferred_provider = 'ai'
            print(f"💡 Telugu to {target_language.upper()} detected - using AI translation for better accuracy")
        
        # Translate using robust translator
        if use_two_step:
            translation_result = self.robust_translator.translate_two_step(
                source_text,
                target_language,
                source_language,
                preferred_provider
            )
        else:
            translation_result = self.robust_translator.translate(
                source_text,
                target_language,
                source_language,
                preferred_provider,
                use_sentence_by_sentence=use_sentence_by_sentence,
                enable_paragraph_retranslation=enable_paragraph_retranslation
            )
        
        return {
            'original_text': source_text,
            'translated_text': translation_result['text'],
            'source_language': source_language,
            'target_language': target_language,
            'translation': translation_result,
            'normalized': translation_result.get('normalized', False),
            'sentence_count': translation_result.get('sentence_count', 0),
            'refined': translation_result.get('refined', False),
            'provider': translation_result.get('provider', 'none'),
            'used_preferred_provider': translation_result.get('used_preferred_provider', True),
            'fallback_provider': translation_result.get('fallback_provider'),
            'secondary_provider': translation_result.get('secondary_provider'),
            'paragraph_retranslation': translation_result.get('paragraph_retranslation', False)
        }
    
    def get_available_providers(self) -> list:
        """Get list of available translation providers"""
        return self.robust_translator.get_available_providers()
    
    def translate_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preferred_provider: Optional[str] = None
    ) -> str:
        """
        Translate plain text (for note translation)
        Uses robust translator for better quality
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            preferred_provider: Preferred provider name
            
        Returns:
            Translated text
        """
        if not text or not text.strip():
            return text
        
        if source_language == target_language:
            return text
        
        translation_result = self.robust_translator.translate(
            text=text,
            target_language=target_language,
            source_language=source_language,
            preferred_provider=preferred_provider,
            use_sentence_by_sentence=True
        )
        
        return translation_result.get('text', text)
    
    def translate_segments(
        self,
        segments: List[Dict[str, Any]],
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Translate transcription segments (for subtitle generation)
        
        Args:
            segments: List of segment dictionaries with 'text' field
            target_language: Target language code
            source_language: Source language code (optional)
            preferred_provider: Preferred provider name
            
        Returns:
            List of segments with translated text
        """
        if not segments:
            return []
        
        # Translate each segment individually using robust translator
        translated_segments = []
        for i, original_seg in enumerate(segments):
            text = original_seg.get('text', '')
            if not text or not text.strip():
                # Empty segment - keep as is with all original metadata
                translated_seg = original_seg.copy()
                translated_seg['original_text'] = text
                translated_segments.append(translated_seg)
                continue
            
            try:
                # Translate this segment
                translation_result = self.robust_translator.translate(
                    text=text,
                    target_language=target_language,
                    source_language=source_language,
                    preferred_provider=preferred_provider,
                    use_sentence_by_sentence=True
                )
                
                translated_text = translation_result.get('text', text)
                
                # Create translated segment - CRITICAL: Preserve ALL original metadata
                translated_seg = original_seg.copy()  # This preserves start, end, and all other fields
                translated_seg['text'] = translated_text  # Only update the text field
                translated_seg['original_text'] = text  # Store original for reference
                
                # CRITICAL: Ensure start and end timestamps are explicitly preserved
                if 'start' not in translated_seg:
                    translated_seg['start'] = original_seg.get('start', 0.0)
                if 'end' not in translated_seg:
                    translated_seg['end'] = original_seg.get('end', original_seg.get('start', 0.0) + 2.0)
                
                translated_segments.append(translated_seg)
            except Exception as e:
                # If translation fails, keep original text but preserve structure
                print(f"⚠️  Failed to translate segment {i+1}: {e}")
                translated_seg = original_seg.copy()
                translated_seg['original_text'] = text
                # Ensure timestamps are preserved
                if 'start' not in translated_seg:
                    translated_seg['start'] = original_seg.get('start', 0.0)
                if 'end' not in translated_seg:
                    translated_seg['end'] = original_seg.get('end', original_seg.get('start', 0.0) + 2.0)
                translated_segments.append(translated_seg)
        
        return translated_segments
    
    @property
    def translation_service(self):
        """Compatibility property - returns robust translator"""
        return self.robust_translator
