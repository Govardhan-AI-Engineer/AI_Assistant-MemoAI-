"""
LLM-based translation refinement using free/open-source models
Supports local models like LLaMA, Mistral, etc.
"""
from typing import Optional, Dict
import re


class LLMRefiner:
    """
    Refines translations using free/open-source LLM models
    Only fixes grammar and readability, does NOT add/remove/invent content
    """
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize LLM refiner
        
        Args:
            model: Model name (e.g., 'llama3', 'mistral', 'phi')
                  If None, uses rule-based refinement as fallback
        """
        self.model = model
        self.llm_available = False
        
        # Try to initialize LLM if model specified
        if model:
            try:
                # Try to import and initialize LLM
                # This is a placeholder - actual implementation depends on chosen library
                # Options: llama-cpp-python, transformers, ollama, etc.
                self._init_llm(model)
                self.llm_available = True
            except ImportError:
                print(f"WARNING: LLM library not available for model '{model}'")
                print("         Using rule-based refinement instead")
                self.llm_available = False
            except Exception as e:
                print(f"WARNING: Failed to initialize LLM: {e}")
                print("         Using rule-based refinement instead")
                self.llm_available = False
    
    def _init_llm(self, model: str):
        """
        Initialize LLM (placeholder - implement based on chosen library)
        
        Examples:
        - llama-cpp-python: from llama_cpp import Llama
        - transformers: from transformers import AutoModelForCausalLM, AutoTokenizer
        - ollama: import ollama
        """
        # Placeholder - implement based on your chosen LLM library
        # For now, we'll use rule-based refinement
        pass
    
    def refine(
        self,
        translated_text: str,
        source_language: str,
        target_language: str,
        original_text: Optional[str] = None
    ) -> str:
        """
        Refine translated text to fix grammar and readability
        Does NOT add, remove, invent, or summarize content
        
        Args:
            translated_text: Translated text to refine
            source_language: Source language code
            target_language: Target language code
            original_text: Original source text (for context, optional)
            
        Returns:
            Refined translated text
        """
        if not translated_text or not translated_text.strip():
            return translated_text
        
        if self.llm_available and self.model:
            # Use LLM-based refinement
            return self._refine_with_llm(translated_text, source_language, target_language, original_text)
        else:
            # Use rule-based refinement
            return self._refine_with_rules(translated_text, target_language)
    
    def _refine_with_llm(
        self,
        translated_text: str,
        source_language: str,
        target_language: str,
        original_text: Optional[str] = None
    ) -> str:
        """
        Refine using LLM (placeholder - implement based on chosen library)
        
        Prompt template:
        "Fix grammar and readability of this translation from {source_language} to {target_language}.
        Do NOT add, remove, invent, or summarize content. Only fix grammar and readability.
        
        Translation to fix:
        {translated_text}
        
        Refined translation:"
        """
        # Placeholder - implement LLM call here
        # For now, fall back to rule-based
        return self._refine_with_rules(translated_text, target_language)
    
    def _refine_with_rules(self, text: str, target_language: str) -> str:
        """
        Rule-based refinement (fallback when LLM not available)
        Fixes common grammar and readability issues
        
        Args:
            text: Text to refine
            target_language: Target language code
            
        Returns:
            Refined text
        """
        refined = text
        
        # Fix common issues in English translations
        if target_language == 'en':
            # Fix double spaces
            refined = re.sub(r' +', ' ', refined)
            
            # Fix missing spaces after punctuation
            refined = re.sub(r'([.!?])([A-Za-z])', r'\1 \2', refined)
            
            # Fix capitalization at sentence start
            sentences = re.split(r'([.!?]+)', refined)
            fixed_sentences = []
            for i, part in enumerate(sentences):
                if not part.strip():
                    fixed_sentences.append(part)
                    continue
                
                # If this is text (not punctuation) and previous was punctuation or start
                if i == 0 or (i > 0 and re.match(r'^[.!?]+$', sentences[i-1])):
                    # Capitalize first letter
                    if part and part[0].islower():
                        part = part[0].upper() + part[1:] if len(part) > 1 else part.upper()
                
                fixed_sentences.append(part)
            
            refined = ''.join(fixed_sentences)
            
            # Fix common grammar issues
            # "how do you know?" -> ensure proper spacing
            refined = re.sub(r'\bhow\s+do\s+you\s+know\?', 'How do you know?', refined, flags=re.IGNORECASE)
            
            # Remove duplicate words at sentence boundaries
            refined = re.sub(r'\b(\w+)\s+\1\b', r'\1', refined, flags=re.IGNORECASE)
        
        # Clean up extra whitespace
        refined = re.sub(r'\n{3,}', '\n\n', refined)
        refined = re.sub(r' +', ' ', refined)
        refined = refined.strip()
        
        return refined
    
    def is_available(self) -> bool:
        """Check if LLM refinement is available"""
        return self.llm_available
