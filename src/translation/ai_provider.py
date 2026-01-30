"""
AI Translation provider using Groq API and Hugging Face Inference API
Primary: Groq API (fast, free tier available)
Fallback: Hugging Face Inference API (free tier)
"""
from typing import List, Optional
import time
import json
import os

# Try to import Groq API (primary option - fast, free tier available)
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None

# Try to import Hugging Face Inference API (fallback option)
try:
    from huggingface_hub import InferenceClient
    HF_INFERENCE_AVAILABLE = True
except ImportError:
    HF_INFERENCE_AVAILABLE = False
    InferenceClient = None

from src.translation.base_provider import TranslationProvider
from src.translation.exceptions import TranslationError, TranslationTimeoutError
from src.core.languages import Languages


class AITranslationProvider(TranslationProvider):
    """
    AI Translation provider using Groq API and Hugging Face
    Primary: Groq API (fast, requires API key from .env)
    Fallback: Hugging Face Inference API (free tier)
    """
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-8b-instant", hf_model: Optional[str] = None):
        """
        Initialize AI translation provider
        
        Args:
            api_key: Groq API key (from environment or parameter)
            model: Groq model name (e.g., 'llama-3.1-8b-instant', 'llama-3.1-70b-versatile', 'mixtral-8x7b-32768')
                  Default: 'llama-3.1-8b-instant' (fast, good for translation)
            hf_model: Hugging Face model ID (fallback option)
                     If None, uses a default free model
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model
        self.hf_model = hf_model or "meta-llama/Meta-Llama-3-8B-Instruct"
        self.groq_available = False
        self.hf_available = False
        self.groq_client = None
        
        # Initialize Groq if API key is available
        if self.api_key and GROQ_AVAILABLE:
            try:
                self.groq_client = Groq(api_key=self.api_key)
                # Test with a simple request to verify API key
                try:
                    test_response = self.groq_client.chat.completions.create(
                        model=self.model,
                        messages=[{"role": "user", "content": "test"}],
                        max_tokens=1
                    )
                    self.groq_available = True
                    print(f"✅ Groq API initialized with model: {self.model}")
                except Exception as test_error:
                    print(f"⚠️  Groq API key validation failed: {test_error}")
                    print("   Please check your GROQ_API_KEY in .env file")
            except Exception as e:
                print(f"⚠️  Groq API initialization failed: {e}")
        elif not self.api_key:
            print("⚠️  GROQ_API_KEY not found in environment variables")
            print("   Add GROQ_API_KEY to your .env file")
        elif not GROQ_AVAILABLE:
            print("⚠️  Groq package not installed")
            print("   Install with: pip install groq")
        
        # Initialize Hugging Face if Groq not available
        if not self.groq_available and HF_INFERENCE_AVAILABLE:
            try:
                self.hf_client = InferenceClient(model=self.hf_model)
                # Test with a simple request
                self.hf_available = True
                print(f"✅ Hugging Face Inference API initialized with model: {self.hf_model}")
            except Exception as e:
                print(f"⚠️  Hugging Face Inference API not available: {e}")
        
        if not self.groq_available and not self.hf_available:
            raise ImportError(
                "No AI translation provider available.\n"
                "Install one of:\n"
                "  1. Groq API (recommended): pip install groq\n"
                "     Then add GROQ_API_KEY to your .env file\n"
                "     Get API key from: https://console.groq.com\n"
                "  2. Hugging Face: pip install huggingface_hub\n"
            )
        
        self._last_request_time = 0
        self._min_request_interval = 0.5  # 500ms between requests
    
    @property
    def name(self) -> str:
        if self.groq_available:
            return f"AI Translation (Groq: {self.model})"
        elif self.hf_available:
            return f"AI Translation (HF: {self.hf_model.split('/')[-1]})"
        return "AI Translation"
    
    @property
    def is_available(self) -> bool:
        """Check if AI translation provider is available"""
        return self.groq_available or self.hf_available
    
    def _get_language_name(self, lang_code: str) -> str:
        """Get full language name from code"""
        return Languages.get_language_name(lang_code) or lang_code
    
    def _create_translation_prompt(
        self,
        text: str,
        source_language: Optional[str],
        target_language: str
    ) -> str:
        """
        Create a prompt for LLM translation
        
        Args:
            text: Text to translate
            source_language: Source language code
            target_language: Target language code
            
        Returns:
            Formatted prompt for LLM
        """
        source_name = self._get_language_name(source_language) if source_language else "the source language"
        target_name = self._get_language_name(target_language)
        
        prompt = f"""Translate the following text from {source_name} to {target_name}.

Requirements:
- Translate accurately and preserve the original meaning
- Maintain natural, fluent language
- Preserve any cultural context or nuances
- Do NOT add, remove, or summarize content
- Only provide the translation, no explanations

Text to translate:
{text}

Translation:"""
        
        return prompt
    
    def translate(
        self,
        text: str,
        target_language: str,
        source_language: Optional[str] = None
    ) -> str:
        """
        Translate text using AI/LLM
        
        Args:
            text: Text to translate
            target_language: Target language code
            source_language: Source language code (optional)
            
        Returns:
            Translated text
            
        Raises:
            TranslationError: If translation fails
        """
        if not text or not text.strip():
            return text
        
        if not self.is_available:
            raise TranslationError("AI translation provider is not available")
        
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        if time_since_last < self._min_request_interval:
            time.sleep(self._min_request_interval - time_since_last)
        self._last_request_time = time.time()
        
        # Create prompt
        prompt = self._create_translation_prompt(text, source_language, target_language)
        
        try:
            if self.groq_available:
                try:
                    return self._translate_with_groq(prompt)
                except Exception as groq_error:
                    # Groq failed during translation, try Hugging Face if available
                    if self.hf_available:
                        print(f"⚠️  Groq translation failed: {groq_error}")
                        print("   Falling back to Hugging Face...")
                        try:
                            return self._translate_with_hf(prompt)
                        except Exception as hf_error:
                            raise TranslationError(
                                f"Both Groq and Hugging Face failed. "
                                f"Groq error: {str(groq_error)}, "
                                f"HF error: {str(hf_error)}"
                            )
                    else:
                        raise TranslationError(f"Groq translation failed: {str(groq_error)}")
            elif self.hf_available:
                return self._translate_with_hf(prompt)
            else:
                raise TranslationError("No AI translation backend available")
        except TranslationError:
            # Re-raise translation errors as-is
            raise
        except Exception as e:
            raise TranslationError(f"AI translation failed: {str(e)}")
    
    def _translate_with_groq(self, prompt: str) -> str:
        """Translate using Groq API"""
        try:
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Lower temperature for more consistent translations
                max_tokens=2048,
                top_p=0.9
            )
            
            translated_text = response.choices[0].message.content.strip()
            
            # Clean up the response (remove any extra formatting)
            translated_text = self._clean_llm_response(translated_text)
            
            if not self.validate_output(translated_text):
                raise TranslationError("Groq translation produced invalid output")
            
            return translated_text
        except Exception as e:
            raise TranslationError(f"Groq translation failed: {str(e)}")
    
    def _translate_with_hf(self, prompt: str) -> str:
        """Translate using Hugging Face Inference API"""
        try:
            response = self.hf_client.text_generation(
                prompt=prompt,
                max_new_tokens=512,
                temperature=0.3,
                top_p=0.9,
                return_full_text=False
            )
            
            # HF API returns the generated text directly
            translated_text = response.strip() if isinstance(response, str) else str(response).strip()
            
            # Clean up the response
            translated_text = self._clean_llm_response(translated_text)
            
            if not self.validate_output(translated_text):
                raise TranslationError("AI translation produced invalid output")
            
            return translated_text
        except Exception as e:
            raise TranslationError(f"Hugging Face translation failed: {str(e)}")
    
    def _clean_llm_response(self, text: str) -> str:
        """
        Clean LLM response to extract just the translation
        
        Args:
            text: Raw LLM response
            
        Returns:
            Cleaned translation text
        """
        # Remove common LLM response prefixes
        prefixes_to_remove = [
            "Translation:",
            "Here's the translation:",
            "The translation is:",
            "Translated text:",
        ]
        
        cleaned = text.strip()
        
        # Remove prefixes
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        # Remove quotes if the entire response is quoted
        if (cleaned.startswith('"') and cleaned.endswith('"')) or \
           (cleaned.startswith("'") and cleaned.endswith("'")):
            cleaned = cleaned[1:-1].strip()
        
        # Remove markdown code blocks if present
        if cleaned.startswith("```") and cleaned.endswith("```"):
            lines = cleaned.split('\n')
            if len(lines) > 2:
                cleaned = '\n'.join(lines[1:-1]).strip()
        
        return cleaned.strip()
    
    def translate_batch(
        self,
        texts: List[str],
        target_language: str,
        source_language: Optional[str] = None
    ) -> List[str]:
        """
        Translate multiple texts using AI/LLM
        
        Args:
            texts: List of texts to translate
            target_language: Target language code
            source_language: Source language code (optional)
            
        Returns:
            List of translated texts
        """
        translated = []
        for text in texts:
            try:
                result = self.translate(text, target_language, source_language)
                translated.append(result)
            except Exception as e:
                # If batch translation fails for one item, return error for that item
                raise TranslationError(f"Batch translation failed: {str(e)}")
        
        return translated
