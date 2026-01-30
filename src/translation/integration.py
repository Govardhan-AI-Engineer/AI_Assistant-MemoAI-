"""
Integration layer for translation with transcription results
"""
from typing import Dict, List, Optional
from src.translation import TranslationService, TranslationGranularity
from src.core.config import Config
from src.translation.exceptions import TranslationError


class TranscriptionTranslationIntegration:
    """
    Integrates translation with transcription results
    """
    
    def __init__(
        self,
        provider_priority: Optional[List[str]] = None,
        enable_retranslation: bool = None
    ):
        """
        Initialize translation integration
        
        Args:
            provider_priority: Provider priority order (default from config)
            enable_retranslation: Enable re-translation (default from config)
            
        Raises:
            ImportError: If TranslationService is not available (dependencies missing)
        """
        # Check if TranslationService is available
        if TranslationService is None:
            raise ImportError(
                "TranslationService is not available. "
                "Please install required dependencies:\n"
                "  pip install googletrans==4.0.0rc1\n"
                "  pip install deep-translator>=1.11.4"
            )
        
        if provider_priority is None:
            provider_priority = Config.TRANSLATION_PROVIDER_PRIORITY
        
        if enable_retranslation is None:
            enable_retranslation = Config.ENABLE_RETRANSLATION
        
        try:
            self.translation_service = TranslationService(
                provider_priority=provider_priority,
                enable_retranslation=enable_retranslation
            )
        except Exception as e:
            raise TranslationError(
                f"Failed to initialize translation service: {str(e)}\n"
                "Please check your configuration and ensure at least one translation provider is available."
            ) from e
    
    def translate_transcription(
        self,
        transcription_result: Dict,
        target_language: str,
        granularity: TranslationGranularity = TranslationGranularity.PARAGRAPH,
        preferred_provider: Optional[str] = None
    ) -> Dict:
        """
        Translate transcription result
        
        Args:
            transcription_result: Transcription result dictionary with 'text' and 'language'
            target_language: Target language code
            granularity: Translation granularity
            preferred_provider: Preferred provider name
            
        Returns:
            Dictionary with original and translated text
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
        
        # Translate
        translation_result = self.translation_service.translate(
            text=source_text,
            target_language=target_language,
            source_language=source_language,
            granularity=granularity,
            preferred_provider=preferred_provider
        )
        
        return {
            'original_text': source_text,
            'translated_text': translation_result['text'],
            'source_language': source_language,
            'target_language': target_language,
            'translation': translation_result
        }
    
    def translate_segments(
        self,
        segments: List[Dict],
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> List[Dict]:
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
        
        # Extract texts
        texts = [seg.get('text', '') for seg in segments]
        
        # Translate line by line
        translated_texts = self.translation_service.translate_lines(
            lines=texts,
            target_language=target_language,
            source_language=source_language,
            preferred_provider=preferred_provider
        )
        
        # Create translated segments
        translated_segments = []
        for original_seg, translated_text in zip(segments, translated_texts):
            translated_seg = original_seg.copy()
            translated_seg['text'] = translated_text
            translated_seg['original_text'] = original_seg.get('text', '')
            translated_segments.append(translated_seg)
        
        return translated_segments
    
    def translate_paragraphs(
        self,
        paragraphs: List[Dict],
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> List[Dict]:
        """
        Translate paragraph-level transcription results
        
        Args:
            paragraphs: List of paragraph dictionaries with 'text' field
            target_language: Target language code
            source_language: Source language code (optional)
            preferred_provider: Preferred provider name
            
        Returns:
            List of paragraphs with translated text
        """
        if not paragraphs:
            return []
        
        # Extract texts
        texts = [para.get('text', '') for para in paragraphs]
        
        # Translate paragraphs
        translated_texts = self.translation_service.translate_paragraphs(
            paragraphs=texts,
            target_language=target_language,
            source_language=source_language,
            preferred_provider=preferred_provider
        )
        
        # Create translated paragraphs
        translated_paragraphs = []
        for original_para, translated_text in zip(paragraphs, translated_texts):
            translated_para = original_para.copy()
            translated_para['text'] = translated_text
            translated_para['original_text'] = original_para.get('text', '')
            translated_paragraphs.append(translated_para)
        
        return translated_paragraphs
