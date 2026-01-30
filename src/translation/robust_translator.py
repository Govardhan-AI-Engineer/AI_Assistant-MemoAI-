"""
Robust translation pipeline for multilingual code-mixed speech
Implements sentence-by-sentence translation with normalization and optional LLM refinement
"""
from typing import List, Optional, Dict, Tuple
from src.translation.base_provider import TranslationGranularity
from src.translation.orchestrator import TranslationOrchestrator
from src.translation.exceptions import TranslationError
from src.translation.text_normalizer import TextNormalizer


class RobustTranslator:
    """
    Robust translation service designed for code-mixed multilingual speech
    Implements:
    - Text normalization (filler removal, sentence fixing)
    - Sentence-by-sentence translation
    - Explicit source language forcing
    - Two-step translation (normalize → translate)
    - Optional LLM-based refinement
    """
    
    def __init__(
        self,
        provider_priority: Optional[List[str]] = None,
        enable_normalization: bool = True,
        enable_llm_refinement: bool = False,
        llm_model: Optional[str] = None
    ):
        """
        Initialize robust translator
        
        Args:
            provider_priority: Provider priority order
            enable_normalization: Enable text normalization before translation
            enable_llm_refinement: Enable LLM-based refinement (requires free/open-source LLM)
            llm_model: LLM model name for refinement (e.g., 'llama3', 'mistral')
        """
        self.orchestrator = TranslationOrchestrator(provider_priority=provider_priority)
        self.enable_normalization = enable_normalization
        self.enable_llm_refinement = enable_llm_refinement
        self.llm_model = llm_model
        
        # Initialize LLM refinement if enabled
        self.llm_refiner = None
        if enable_llm_refinement:
            try:
                from src.translation.llm_refiner import LLMRefiner
                self.llm_refiner = LLMRefiner(model=llm_model)
            except ImportError:
                print("WARNING: LLM refinement requested but LLMRefiner not available")
                print("         Install required dependencies or disable LLM refinement")
                self.enable_llm_refinement = False
    
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None,
        normalize_text: Optional[bool] = None,
        use_sentence_by_sentence: bool = True,
        enable_refinement: Optional[bool] = None,
        enable_paragraph_retranslation: bool = False
    ) -> Dict:
        """
        Translate text using robust pipeline
        
        Args:
            text: Text to translate
            target_language: Target language code (e.g., 'en')
            source_language: Source language code (MUST be provided, no auto-detect)
            preferred_provider: Preferred provider name
            normalize_text: Override normalization setting
            use_sentence_by_sentence: Translate sentence-by-sentence (recommended)
            enable_refinement: Override LLM refinement setting
            
        Returns:
            Dictionary with translation results and metadata
        """
        if not text or not text.strip():
            return {
                'text': text,
                'provider': 'none',
                'normalized': False,
                'sentence_count': 0,
                'refined': False
            }
        
        # Force source language - no auto-detect
        if not source_language:
            raise TranslationError(
                "Source language must be explicitly provided. "
                "Auto-detection is disabled for robust translation."
            )
        
        # Step 1: Normalize text
        should_normalize = normalize_text if normalize_text is not None else self.enable_normalization
        normalized_text = text
        normalization_applied = False
        
        if should_normalize:
            normalizer = TextNormalizer(source_language=source_language)
            normalized_text = normalizer.normalize(
                text,
                remove_fillers=True,
                fix_sentences=True,
                handle_code_mixed=True
            )
            normalization_applied = (normalized_text != text)
        
        # Step 2: Split into sentences
        if use_sentence_by_sentence:
            normalizer = TextNormalizer(source_language=source_language)
            sentences = normalizer.split_into_sentences(normalized_text)
        else:
            # Use whole text
            sentences = [normalized_text]
        
        # Step 3: Translate each sentence with explicit source language
        translated_sentences = []
        provider_used = None
        used_preferred = True
        fallback_provider = None
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            try:
                # Translate with explicit source language (no auto-detect)
                translated, provider, used_pref, fallback_prov = self.orchestrator.translate_with_fallback(
                    sentence.strip(),
                    target_language,
                    source_language,  # Explicit source - no None
                    preferred_provider
                )
                
                translated_sentences.append(translated.strip())
                
                # Track provider usage
                if not provider_used:
                    provider_used = provider
                if not used_pref:
                    used_preferred = False
                    if not fallback_provider:
                        fallback_provider = fallback_prov
                        
            except Exception as e:
                # If translation fails for a sentence, keep original
                print(f"WARNING: Failed to translate sentence: {sentence[:50]}... Error: {e}")
                translated_sentences.append(sentence.strip())
        
        # Join translated sentences
        translated_text = ' '.join(translated_sentences)
        
        # Step 4: Optional paragraph-level re-translation for quality refinement
        secondary_provider = None
        if enable_paragraph_retranslation:
            try:
                # Split into paragraphs and re-translate each with secondary provider
                normalizer = TextNormalizer(source_language=source_language)
                paragraphs = self._split_into_paragraphs(translated_text)
                
                if len(paragraphs) > 1:
                    # Get secondary provider (next available after primary)
                    secondary_prov = self._get_secondary_provider(preferred_provider or provider_used)
                    
                    if secondary_prov:
                        retranslated_paragraphs = []
                        for para in paragraphs:
                            if not para.strip():
                                retranslated_paragraphs.append(para)
                                continue
                            
                            try:
                                # Re-translate paragraph with secondary provider
                                retranslated, _, _ = self.orchestrator.retranslate(
                                    para.strip(),
                                    target_language,
                                    source_language,
                                    preferred_provider or provider_used,
                                    secondary_prov
                                )
                                retranslated_paragraphs.append(retranslated.strip())
                                if not secondary_provider:
                                    secondary_provider = secondary_prov
                            except Exception as e:
                                # If re-translation fails, use original
                                print(f"WARNING: Paragraph re-translation failed: {e}")
                                retranslated_paragraphs.append(para)
                        
                        if retranslated_paragraphs:
                            translated_text = '\n\n'.join(retranslated_paragraphs)
            except Exception as e:
                print(f"WARNING: Paragraph-level re-translation failed: {e}")
                # Continue with original translation
        
        # Step 5: Optional LLM refinement
        refined = False
        should_refine = enable_refinement if enable_refinement is not None else self.enable_llm_refinement
        
        if should_refine and self.llm_refiner:
            try:
                refined_text = self.llm_refiner.refine(
                    translated_text,
                    source_language,
                    target_language,
                    original_text=text
                )
                if refined_text and refined_text.strip():
                    translated_text = refined_text
                    refined = True
            except Exception as e:
                print(f"WARNING: LLM refinement failed: {e}")
                # Continue with unrefined translation
        
        return {
            'text': translated_text,
            'provider': provider_used or 'none',
            'source_language': source_language,
            'target_language': target_language,
            'normalized': normalization_applied,
            'sentence_count': len(sentences),
            'refined': refined,
            'used_preferred_provider': used_preferred,
            'fallback_provider': fallback_provider,
            'secondary_provider': secondary_provider,
            'paragraph_retranslation': enable_paragraph_retranslation and secondary_provider is not None,
            'original_text': text,
            'normalized_text': normalized_text if normalization_applied else None
        }
    
    def translate_two_step(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None,
        preferred_provider: Optional[str] = None
    ) -> Dict:
        """
        Two-step translation: First normalize to clean source language, then translate
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (MUST be provided)
            preferred_provider: Preferred provider name
            
        Returns:
            Dictionary with translation results
        """
        if not source_language:
            raise TranslationError("Source language must be provided for two-step translation")
        
        # Step 1: Normalize text in source language
        normalizer = TextNormalizer(source_language=source_language)
        normalized = normalizer.normalize(
            text,
            remove_fillers=True,
            fix_sentences=True,
            handle_code_mixed=True
        )
        
        # Step 2: Translate normalized text
        return self.translate(
            normalized,
            target_language,
            source_language,
            preferred_provider,
            normalize_text=False,  # Already normalized
            use_sentence_by_sentence=True
        )
    
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
