"""
Text normalization for multilingual transcription, especially code-mixed Indian speech
Handles filler words, sentence boundaries, and code-mixed Hinglish/Indic speech
"""
import re
from typing import List, Optional, Dict, Set


class TextNormalizer:
    """
    Normalizes transcription text before translation
    Handles filler words, sentence boundaries, and code-mixed speech
    """
    
    # Common filler words in Indian languages (transliterated and native)
    FILLER_WORDS: Dict[str, Set[str]] = {
        'hi': {
            'na', 'ji', 'arre', 'yaar', 'ya', 'to', 'hai', 'ho', 'tha', 'thi', 'the',
            'ka', 'ki', 'ke', 'ko', 'se', 'me', 'par', 'aur', 'bhi', 'toh', 'hain',
            'baivi', 'aagaya', 'aaya', 'gaya', 'gayi', 'gaye'
        },
        'te': {
            'anna', 'akka', 'baava', 'ra', 'ga', 'na', 'le', 've', 'ye', 'o',
            'unnaru', 'unnaru', 'unnayi', 'unnayi', 'undhi', 'undhi', 'unnaru'
        },
        'ta': {
            'anna', 'akka', 'da', 'ra', 'na', 'la', 'va', 'ya', 'o'
        },
        'kn': {
            'anna', 'akka', 'ra', 'na', 'la', 'va', 'ya', 'o'
        },
        'ml': {
            'chetta', 'chechi', 'ra', 'na', 'la', 'va', 'ya', 'o'
        },
        'en': set()  # English has minimal fillers in transcription context
    }
    
    # Sentence ending patterns
    SENTENCE_ENDINGS = re.compile(r'[.!?]+')
    
    # Multiple punctuation pattern (e.g., "!!!" or "...")
    MULTIPLE_PUNCTUATION = re.compile(r'([.!?])\1{2,}')
    
    def __init__(self, source_language: Optional[str] = None):
        """
        Initialize text normalizer
        
        Args:
            source_language: Source language code (e.g., 'hi', 'te', 'en')
        """
        self.source_language = source_language or 'auto'
    
    def normalize(
        self,
        text: str,
        remove_fillers: bool = True,
        fix_sentences: bool = True,
        handle_code_mixed: bool = True
    ) -> str:
        """
        Normalize text with all available techniques
        
        Args:
            text: Raw transcription text
            remove_fillers: Remove filler words
            fix_sentences: Fix sentence boundaries
            handle_code_mixed: Handle code-mixed speech
            
        Returns:
            Normalized text
        """
        if not text or not text.strip():
            return text
        
        normalized = text.strip()
        
        # Step 1: Fix sentence boundaries
        if fix_sentences:
            normalized = self._fix_sentence_boundaries(normalized)
        
        # Step 2: Remove filler words
        if remove_fillers:
            normalized = self._remove_filler_words(normalized)
        
        # Step 3: Handle code-mixed speech
        if handle_code_mixed:
            normalized = self._handle_code_mixed(normalized)
        
        # Step 4: Clean up extra whitespace
        normalized = self._clean_whitespace(normalized)
        
        return normalized
    
    def _fix_sentence_boundaries(self, text: str) -> str:
        """
        Fix sentence boundaries by ensuring proper punctuation
        
        Args:
            text: Input text
            
        Returns:
            Text with fixed sentence boundaries
        """
        # Normalize multiple punctuation marks
        text = self.MULTIPLE_PUNCTUATION.sub(r'\1', text)
        
        # Ensure sentences end with proper punctuation
        # If a sentence doesn't end with punctuation, add period
        lines = text.split('\n')
        fixed_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                fixed_lines.append('')
                continue
            
            # Split by existing sentence endings
            sentences = self.SENTENCE_ENDINGS.split(line)
            sentence_parts = []
            
            for i, part in enumerate(sentences):
                part = part.strip()
                if not part:
                    continue
                
                # If this part doesn't end with punctuation and isn't the last part
                # (which might naturally not have punctuation if it's the end of line)
                if i < len(sentences) - 1:
                    # This should have ended with punctuation (it was split by it)
                    # But check if it needs capitalization
                    if part and not part[0].isupper():
                        # Capitalize first letter if it's a new sentence
                        part = part[0].upper() + part[1:] if len(part) > 1 else part.upper()
                
                sentence_parts.append(part)
            
            # Rejoin with proper punctuation
            if sentence_parts:
                # Join sentences with periods if they don't have punctuation
                result = '. '.join(sentence_parts)
                # Ensure it ends with punctuation
                if result and not self.SENTENCE_ENDINGS.search(result[-1]):
                    result += '.'
                fixed_lines.append(result)
            else:
                fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)
    
    def _remove_filler_words(self, text: str) -> str:
        """
        Remove filler words based on source language
        
        Args:
            text: Input text
            
        Returns:
            Text with filler words removed
        """
        if self.source_language == 'auto':
            # Try to detect and remove common fillers across languages
            fillers = set()
            for lang_fillers in self.FILLER_WORDS.values():
                fillers.update(lang_fillers)
        else:
            # Get fillers for specific language
            fillers = self.FILLER_WORDS.get(self.source_language, set())
            # Also include common fillers that appear across languages
            fillers.update(self.FILLER_WORDS.get('hi', set()))
        
        if not fillers:
            return text
        
        # Create regex pattern for filler words
        # Match whole words only (with word boundaries)
        filler_pattern = r'\b(' + '|'.join(re.escape(f) for f in fillers) + r')\b'
        
        # Remove filler words (case-insensitive)
        text = re.sub(filler_pattern, '', text, flags=re.IGNORECASE)
        
        return text
    
    def _handle_code_mixed(self, text: str) -> str:
        """
        Handle code-mixed speech (e.g., Hinglish)
        This normalizes mixed language patterns
        
        Args:
            text: Input text
            
        Returns:
            Text with code-mixed patterns normalized
        """
        # Common code-mixed patterns to normalize
        
        # Pattern: "word na ji" -> "word"
        text = re.sub(r'\s+na\s+ji\s+', ' ', text, flags=re.IGNORECASE)
        
        # Pattern: "word baivi" -> "word"
        text = re.sub(r'\s+baivi\s+', ' ', text, flags=re.IGNORECASE)
        
        # Pattern: "aagaya/aaya" -> normalize to consistent form
        text = re.sub(r'\baagaya\b', 'aaya', text, flags=re.IGNORECASE)
        
        # Pattern: Multiple "ji" or "na" in sequence -> remove duplicates
        text = re.sub(r'\b(ji|na)\s+\1\b', r'\1', text, flags=re.IGNORECASE)
        
        # Pattern: "anna" at start of sentence (addressing) -> keep but normalize spacing
        text = re.sub(r'\banna\s+', 'Anna ', text)
        
        return text
    
    def _clean_whitespace(self, text: str) -> str:
        """
        Clean up extra whitespace
        
        Args:
            text: Input text
            
        Returns:
            Text with normalized whitespace
        """
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple newlines with double newline (paragraph break)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove leading/trailing whitespace from each line
        lines = text.split('\n')
        cleaned_lines = [line.strip() for line in lines]
        
        # Remove empty lines at start and end
        while cleaned_lines and not cleaned_lines[0]:
            cleaned_lines.pop(0)
        while cleaned_lines and not cleaned_lines[-1]:
            cleaned_lines.pop()
        
        return '\n'.join(cleaned_lines)
    
    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using robust multilingual sentence splitting
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        if not text or not text.strip():
            return []
        
        # First normalize the text
        normalized = self._clean_whitespace(text)
        
        # Split by sentence endings
        # Use regex to split on sentence endings while preserving them
        sentences = []
        current_sentence = []
        
        # Split by sentence endings
        parts = re.split(r'([.!?]+)', normalized)
        
        for i, part in enumerate(parts):
            if not part.strip():
                continue
            
            # Check if this part is punctuation
            if re.match(r'^[.!?]+$', part):
                # This is punctuation, add to current sentence
                if current_sentence:
                    current_sentence.append(part)
                    sentences.append(''.join(current_sentence).strip())
                    current_sentence = []
            else:
                # This is text
                if current_sentence:
                    # Add space if needed
                    current_sentence.append(' ')
                current_sentence.append(part)
        
        # Add remaining sentence if any
        if current_sentence:
            sentence = ''.join(current_sentence).strip()
            if sentence:
                # Ensure it ends with punctuation
                if not self.SENTENCE_ENDINGS.search(sentence[-1]):
                    sentence += '.'
                sentences.append(sentence)
        
        # Filter out empty sentences
        sentences = [s for s in sentences if s.strip()]
        
        # If no sentences found, return original text as single sentence
        if not sentences:
            sentences = [normalized]
        
        return sentences
