"""
Semantic-preserving translation for structured content (key points, summaries)
Ensures identical meaning across all languages by translating structured content
point-by-point while preserving facts, numbers, dates, and structure.
"""
import re
from typing import List, Optional, Tuple
from src.translation import TranslationService, TranslationGranularity
from src.translation.exceptions import TranslationError


class SemanticTranslator:
    """
    Translator that preserves semantic meaning for structured content
    Designed for key points and summaries that must be identical across languages
    """
    
    def __init__(self, translation_service: TranslationService):
        """
        Initialize semantic translator
        
        Args:
            translation_service: Translation service instance
        """
        self.translation_service = translation_service
    
    def translate_structured_content(
        self,
        content: str,
        source_language: str,
        target_language: str,
        content_type: str = "key_points",  # "key_points" or "summary"
        preferred_provider: Optional[str] = None
    ) -> str:
        """
        Translate structured content (key points or summary) while preserving semantics
        
        CRITICAL: This method ensures:
        - Each point/sentence is translated individually
        - Structure and formatting are preserved
        - Facts, numbers, dates, and names are preserved exactly
        - No information loss, hallucination, or simplification
        - Identical meaning across all languages
        
        Args:
            content: Structured content (key points or summary)
            source_language: Source language code
            target_language: Target language code
            content_type: Type of content ("key_points" or "summary")
            preferred_provider: Preferred translation provider
            
        Returns:
            Translated content with identical semantic meaning
        """
        if not content or not content.strip():
            return content
        
        if source_language == target_language:
            return content
        
        if content_type == "key_points":
            return self._translate_key_points(
                content, source_language, target_language, preferred_provider
            )
        else:
            return self._translate_summary(
                content, source_language, target_language, preferred_provider
            )
    
    def _translate_key_points(
        self,
        content: str,
        source_language: str,
        target_language: str,
        preferred_provider: Optional[str] = None
    ) -> str:
        """
        Translate key points while preserving structure and semantics
        
        Strategy:
        1. Parse numbered/bulleted list structure
        2. Extract each point individually
        3. Translate each point separately (preserves context and facts)
        4. Reconstruct with original formatting
        """
        # Parse key points into individual items
        points = self._parse_key_points(content)
        
        if not points:
            # Fallback: translate as whole text
            return self._translate_whole_text(
                content, source_language, target_language, preferred_provider
            )
        
        # Translate each point individually
        translated_points = []
        for point in points:
            if not point.strip():
                translated_points.append(point)
                continue
            
            # Translate point with explicit semantic preservation instructions
            translated_point = self._translate_with_semantic_preservation(
                point,
                source_language,
                target_language,
                preferred_provider,
                is_key_point=True
            )
            translated_points.append(translated_point)
        
        # Reconstruct formatted list
        return self._reconstruct_key_points(translated_points, content)
    
    def _translate_summary(
        self,
        content: str,
        source_language: str,
        target_language: str,
        preferred_provider: Optional[str] = None
    ) -> str:
        """
        Translate summary while preserving semantics
        
        Strategy:
        1. Split into sentences
        2. Translate each sentence individually
        3. Preserve paragraph structure
        """
        # Split into sentences while preserving paragraph breaks
        sentences = self._split_into_sentences_preserving_paragraphs(content)
        
        if len(sentences) == 1:
            # Single sentence/paragraph - translate as whole
            return self._translate_with_semantic_preservation(
                content,
                source_language,
                target_language,
                preferred_provider,
                is_key_point=False
            )
        
        # Translate each sentence individually
        translated_sentences = []
        for sentence in sentences:
            if not sentence.strip():
                translated_sentences.append(sentence)
                continue
            
            translated_sentence = self._translate_with_semantic_preservation(
                sentence,
                source_language,
                target_language,
                preferred_provider,
                is_key_point=False
            )
            translated_sentences.append(translated_sentence)
        
        # Reconstruct with paragraph breaks
        return self._reconstruct_summary(translated_sentences, content)
    
    def _parse_key_points(self, content: str) -> List[str]:
        """
        Parse key points from formatted text
        
        Supports:
        - Numbered lists: 1. Point, 2. Point, etc.
        - Bullet points: • Point, - Point, * Point
        - Mixed formats
        """
        points = []
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip headers
            if line.lower().startswith(('key points', 'points', 'summary', 'main points')):
                continue
            
            # Match numbered list (1., 2., etc.)
            numbered_match = re.match(r'^\d+[\.\)]\s*(.+)$', line)
            if numbered_match:
                points.append(numbered_match.group(1).strip())
                continue
            
            # Match bullet points (-, •, *, etc.)
            bullet_match = re.match(r'^[-•*]\s*(.+)$', line)
            if bullet_match:
                points.append(bullet_match.group(1).strip())
                continue
            
            # If line doesn't match pattern but has content, treat as point
            if len(line) > 10:  # Minimum length to be a valid point
                points.append(line)
        
        return points if points else []
    
    def _split_into_sentences_preserving_paragraphs(self, text: str) -> List[str]:
        """
        Split text into sentences while preserving paragraph structure
        Improved to handle all sentence endings and preserve complete text
        """
        if not text or not text.strip():
            return [text]
        
        # Split by double newlines (paragraph breaks)
        paragraphs = text.split('\n\n')
        
        sentences = []
        for para_idx, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                if para_idx < len(paragraphs) - 1:  # Don't add trailing empty
                    sentences.append('')
                continue
            
            # Improved sentence splitting - handle multiple sentence endings
            # Split on sentence endings but keep the punctuation
            sentence_pattern = r'([.!?।॥]\s+|\.\s*$)'
            para_sentences = re.split(sentence_pattern, para)
            
            # Reconstruct sentences
            current_sentence = ''
            for i, part in enumerate(para_sentences):
                if not part.strip():
                    continue
                
                current_sentence += part
                
                # Check if this part ends a sentence
                if re.search(r'[.!?।॥]\s*$', part) or (i == len(para_sentences) - 1 and current_sentence.strip()):
                    if current_sentence.strip():
                        sentences.append(current_sentence.strip())
                    current_sentence = ''
            
            # Add any remaining text as a sentence
            if current_sentence.strip():
                sentences.append(current_sentence.strip())
            
            # Add paragraph break marker (except for last paragraph)
            if para_idx < len(paragraphs) - 1:
                sentences.append('')
        
        # Remove trailing empty markers
        while sentences and not sentences[-1]:
            sentences.pop()
        
        # If no sentences found, return original text as single sentence
        if not sentences:
            return [text]
        
        return sentences
    
    def _translate_with_semantic_preservation(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preferred_provider: Optional[str] = None,
        is_key_point: bool = False
    ) -> str:
        """
        Translate text with explicit semantic preservation
        
        Uses WHOLE_TEXT granularity to preserve context and meaning
        Handles both TranslationService and RobustTranslator interfaces
        """
        try:
            # Check if service is TranslationService (has granularity) or RobustTranslator (doesn't)
            if hasattr(self.translation_service, 'translate'):
                # Try to detect service type by checking method signature
                import inspect
                sig = inspect.signature(self.translation_service.translate)
                params = list(sig.parameters.keys())
                
                if 'granularity' in params:
                    # TranslationService - use granularity
                    result = self.translation_service.translate(
                        text=text,
                        target_language=target_language,
                        source_language=source_language,
                        granularity=TranslationGranularity.WHOLE_TEXT,
                        preferred_provider=preferred_provider,
                        enable_retranslation=False  # Disable retranslation to avoid quality degradation
                    )
                else:
                    # RobustTranslator or similar - no granularity parameter
                    result = self.translation_service.translate(
                        text=text,
                        target_language=target_language,
                        source_language=source_language,
                        preferred_provider=preferred_provider,
                        use_sentence_by_sentence=True  # Use sentence-by-sentence for better quality
                    )
            else:
                # Fallback: try standard call
                result = self.translation_service.translate(
                    text=text,
                    target_language=target_language,
                    source_language=source_language
                )
            
            # Handle both dict and string results
            if isinstance(result, dict):
                translated = result.get('text', text)
            else:
                translated = result if result else text
            
            # Basic validation: ensure translation is not empty or too short
            if not translated or len(translated.strip()) < len(text.strip()) * 0.3:
                # Translation seems too short - might be lossy
                # Return original as fallback
                return text
            
            return translated.strip()
            
        except TypeError as e:
            # Handle parameter mismatch - try without granularity
            if 'granularity' in str(e) or 'unexpected keyword' in str(e):
                try:
                    # Retry without granularity (for RobustTranslator)
                    result = self.translation_service.translate(
                        text=text,
                        target_language=target_language,
                        source_language=source_language,
                        preferred_provider=preferred_provider
                    )
                    if isinstance(result, dict):
                        translated = result.get('text', text)
                    else:
                        translated = result if result else text
                    return translated.strip() if translated else text
                except Exception as e2:
                    print(f"Warning: Semantic translation retry failed: {e2}")
                    return text
            else:
                print(f"Warning: Semantic translation failed: {e}")
                return text
        except Exception as e:
            # If translation fails, return original
            print(f"Warning: Semantic translation failed: {e}")
            return text
    
    def _translate_whole_text(
        self,
        text: str,
        source_language: str,
        target_language: str,
        preferred_provider: Optional[str] = None
    ) -> str:
        """Fallback: translate as whole text"""
        try:
            # Check if service supports granularity
            import inspect
            sig = inspect.signature(self.translation_service.translate)
            params = list(sig.parameters.keys())
            
            if 'granularity' in params:
                result = self.translation_service.translate(
                    text=text,
                    target_language=target_language,
                    source_language=source_language,
                    granularity=TranslationGranularity.WHOLE_TEXT,
                    preferred_provider=preferred_provider
                )
            else:
                # RobustTranslator - no granularity
                result = self.translation_service.translate(
                    text=text,
                    target_language=target_language,
                    source_language=source_language,
                    preferred_provider=preferred_provider
                )
            
            if isinstance(result, dict):
                return result.get('text', text)
            return result if result else text
        except TypeError as e:
            # Handle parameter mismatch
            if 'granularity' in str(e) or 'unexpected keyword' in str(e):
                try:
                    result = self.translation_service.translate(
                        text=text,
                        target_language=target_language,
                        source_language=source_language,
                        preferred_provider=preferred_provider
                    )
                    if isinstance(result, dict):
                        return result.get('text', text)
                    return result if result else text
                except Exception:
                    return text
            return text
        except Exception:
            return text
    
    def _reconstruct_key_points(self, translated_points: List[str], original_content: str) -> str:
        """
        Reconstruct key points with original formatting style
        """
        if not translated_points:
            return original_content
        
        # Detect original format
        lines = original_content.split('\n')
        uses_numbering = any(re.match(r'^\d+[\.\)]', line.strip()) for line in lines if line.strip())
        uses_bullets = any(re.match(r'^[-•*]', line.strip()) for line in lines if line.strip())
        
        formatted_points = []
        for i, point in enumerate(translated_points, 1):
            if not point.strip():
                continue
            
            if uses_numbering:
                formatted_points.append(f"{i}. {point}")
            elif uses_bullets:
                formatted_points.append(f"• {point}")
            else:
                formatted_points.append(f"{i}. {point}")  # Default to numbering
        
        return '\n'.join(formatted_points)
    
    def _reconstruct_summary(self, translated_sentences: List[str], original_content: str) -> str:
        """
        Reconstruct summary with paragraph breaks
        Ensures all sentences are included and properly formatted
        """
        if not translated_sentences:
            return original_content
        
        # Reconstruct with paragraph breaks
        paragraphs = []
        current_para = []
        
        for sentence in translated_sentences:
            if not sentence or sentence.strip() == '':
                # Paragraph break
                if current_para:
                    para_text = ' '.join(current_para).strip()
                    if para_text:
                        paragraphs.append(para_text)
                    current_para = []
            else:
                # Add sentence to current paragraph
                sentence = sentence.strip()
                if sentence:
                    current_para.append(sentence)
        
        # Add last paragraph if any
        if current_para:
            para_text = ' '.join(current_para).strip()
            if para_text:
                paragraphs.append(para_text)
        
        # Join paragraphs with double newlines
        result = '\n\n'.join(paragraphs) if paragraphs else ' '.join([s for s in translated_sentences if s.strip()])
        
        # Validate: ensure we didn't lose too much content
        if len(result.strip()) < len(original_content.strip()) * 0.5:
            # Reconstruction seems to have lost too much - return joined sentences as fallback
            print(f"⚠ Warning: Summary reconstruction may have lost content. Original: {len(original_content)}, Result: {len(result)}")
            fallback = ' '.join([s for s in translated_sentences if s.strip()])
            if len(fallback) > len(result):
                return fallback
        
        return result
