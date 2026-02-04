"""
Note generation and management service
Generates canonical notes in original transcript language
"""
from typing import Optional, Dict, Any
import os

# Try to import Groq for note generation
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None

from src.memory.storage import StorageService
from src.core.config import Config


class NoteService:
    """
    Service for generating and managing canonical notes
    Notes are generated once in the original transcript language
    """
    
    def __init__(self, storage_service: Optional[StorageService] = None):
        """
        Initialize note service
        
        Args:
            storage_service: Storage service instance (creates new if None)
        """
        self.storage = storage_service or StorageService()
        self.groq_client = None
        
        # Initialize Groq if available
        api_key = os.getenv("GROQ_API_KEY")
        if api_key and GROQ_AVAILABLE:
            try:
                self.groq_client = Groq(api_key=api_key)
            except Exception:
                pass
    
    def generate_summary(
        self,
        user_id: int,
        transcript_id: int,
        transcript_text: str,
        language: str,
        model: str = "llama-3.1-8b-instant",
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate canonical summary note from transcript
        CANONICAL: Generated once per transcript, reused for all languages
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID
            transcript_text: Full transcript text
            language: Language of transcript (original language)
            model: Groq model to use
            force_regenerate: If True, regenerate even if note exists
            
        Returns:
            Dictionary with note data
        """
        # Check if canonical summary already exists (deterministic reuse)
        if not force_regenerate:
            existing_notes = self.storage.get_transcript_notes(user_id=user_id, transcript_id=transcript_id)
            for note in existing_notes:
                if note.get('note_type') == 'summary' and note.get('language') == language:
                    # Canonical note exists - return it (deterministic behavior)
                    return note
        
        if not self.groq_client:
            raise ValueError("Groq API not available. Set GROQ_API_KEY in .env file")
        
        # Create prompt for summary generation
        prompt = self._create_summary_prompt(transcript_text, language)
        
        try:
            # Generate summary using Groq (deterministic with temperature=0.0 to prevent hallucination)
            response = self.groq_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a factual summarization assistant. You ONLY summarize information that is explicitly stated in the provided transcript. You NEVER add, infer, or assume information that is not directly present in the transcript. You NEVER use general knowledge or external information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,  # Zero temperature for maximum factuality and no hallucination
                max_tokens=512,
                top_p=0.9  # Nucleus sampling for more focused output
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Post-process to remove hallucinations
            summary = self._remove_hallucinations(summary, transcript_text)
            
            # Save canonical note (in original transcript language)
            note = self.storage.save_note(
                user_id=user_id,
                transcript_id=transcript_id,
                content=summary,
                language=language,
                note_type='summary'
            )
            
            return note
            
        except Exception as e:
            raise Exception(f"Failed to generate summary: {str(e)}")
    
    def generate_key_points(
        self,
        user_id: int,
        transcript_id: int,
        transcript_text: str,
        language: str,
        model: str = "llama-3.1-8b-instant",
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate canonical key points note from transcript
        CANONICAL: Generated once per transcript, reused for all languages
        Ensures exactly 7 key points for consistency
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID
            transcript_text: Full transcript text
            language: Language of transcript (original language)
            model: Groq model to use
            force_regenerate: If True, regenerate even if note exists
            
        Returns:
            Dictionary with note data
        """
        # Check if canonical key points already exist (deterministic reuse)
        if not force_regenerate:
            existing_notes = self.storage.get_transcript_notes(user_id=user_id, transcript_id=transcript_id)
            for note in existing_notes:
                if note.get('note_type') == 'key_points' and note.get('language') == language:
                    # Canonical note exists - return it (deterministic behavior)
                    return note
        
        if not self.groq_client:
            raise ValueError("Groq API not available. Set GROQ_API_KEY in .env file")
        
        # Create prompt for key points (ensures exactly 7 points)
        prompt = self._create_key_points_prompt(transcript_text, language)
        
        try:
            # Generate key points using Groq (deterministic with temperature=0.0 to prevent hallucination)
            response = self.groq_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a factual extraction assistant. You ONLY extract information that is explicitly stated in the provided transcript. You NEVER add, infer, or assume information that is not directly present in the transcript. You NEVER use general knowledge or external information."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,  # Zero temperature for maximum factuality and no hallucination
                max_tokens=512,
                top_p=0.9  # Nucleus sampling for more focused output
            )
            
            key_points = response.choices[0].message.content.strip()
            
            # Post-process to remove hallucinations
            key_points = self._remove_hallucinations(key_points, transcript_text)
            
            # Post-process to ensure proper formatting and exactly 7 points
            key_points = self._format_key_points(key_points)
            
            # Save canonical note (in original transcript language)
            note = self.storage.save_note(
                user_id=user_id,
                transcript_id=transcript_id,
                content=key_points,
                language=language,
                note_type='key_points'
            )
            
            return note
            
        except Exception as e:
            raise Exception(f"Failed to generate key points: {str(e)}")
    
    def _create_summary_prompt(self, text: str, language: str) -> str:
        """Create prompt for summary generation"""
        # Map language codes to full names for better LLM understanding
        language_names = {
            'en': 'English',
            'hi': 'Hindi',
            'te': 'Telugu',
            'ta': 'Tamil',
            'fr': 'French',
            'es': 'Spanish',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'ru': 'Russian'
        }
        lang_name = language_names.get(language, language)
        
        return f"""Generate a concise summary of the following transcript in {lang_name} ({language}).

🚫 STRICT ANTI-HALLUCINATION RULES (CRITICAL):
- You MUST ONLY use information that is EXPLICITLY stated in the transcript below
- You MUST NOT add any information, facts, or details that are NOT in the transcript
- You MUST NOT infer, assume, or guess any information
- You MUST NOT use general knowledge or external information
- You MUST NOT add descriptive phrases like "as we all know", "it is well known", "obviously", "clearly"
- You MUST NOT add conclusions or interpretations that are not explicitly stated
- If information is not in the transcript, DO NOT include it - even if it seems logical or common knowledge
- Every sentence in your summary MUST be directly supported by the transcript text

CRITICAL REQUIREMENTS FOR SEMANTIC CONSISTENCY:
- Summarize ONLY the main points and key information that are EXPLICITLY in the transcript
- Keep it concise (2-3 paragraphs)
- PRESERVE ALL FACTS, NUMBERS, DATES, NAMES, AND SPECIFIC DETAILS EXACTLY as they appear
- Do NOT simplify, omit, or change any factual information
- Do NOT add information that is not in the transcript
- Maintain the same level of detail and emphasis as the original
- Write the summary in {lang_name} language
- Ensure the summary can be translated to other languages while maintaining identical meaning

VALIDATION CHECK:
Before writing your summary, verify that every fact, number, date, and name you include is explicitly mentioned in the transcript below. If you cannot find it in the transcript, DO NOT include it.

Transcript:
{text}

Summary (in {lang_name}, preserving all facts and details, using ONLY information from the transcript above):"""
    
    def _create_key_points_prompt(self, text: str, language: str) -> str:
        """Create prompt for key points generation"""
        # Map language codes to full names for better LLM understanding
        language_names = {
            'en': 'English',
            'hi': 'Hindi',
            'te': 'Telugu',
            'ta': 'Tamil',
            'fr': 'French',
            'es': 'Spanish',
            'de': 'German',
            'it': 'Italian',
            'pt': 'Portuguese',
            'ja': 'Japanese',
            'ko': 'Korean',
            'zh': 'Chinese',
            'ar': 'Arabic',
            'ru': 'Russian'
        }
        lang_name = language_names.get(language, language)
        
        return f"""Extract exactly 7 key points from the following transcript in {lang_name} ({language}).

🚫 STRICT ANTI-HALLUCINATION RULES (CRITICAL):
- You MUST ONLY extract information that is EXPLICITLY stated in the transcript below
- You MUST NOT add any information, facts, or details that are NOT in the transcript
- You MUST NOT infer, assume, or guess any information
- You MUST NOT use general knowledge or external information
- You MUST NOT add descriptive phrases like "as we all know", "it is well known", "obviously", "clearly", "as observed by everyone"
- You MUST NOT add conclusions or interpretations that are not explicitly stated
- If information is not in the transcript, DO NOT include it - even if it seems logical or common knowledge
- Every point you extract MUST be directly supported by the transcript text
- If the transcript has fewer than 7 distinct points, extract only what is available (but try to find 7 if possible)

CRITICAL FORMATTING REQUIREMENTS (MUST FOLLOW EXACTLY):
- Extract EXACTLY 7 main points (no more, no less) - but ONLY if 7 distinct points exist in the transcript
- Format STRICTLY as a numbered list: "1. " followed by the point text, then newline, then "2. " etc.
- Each point MUST be on a separate line
- Start each line with the number followed by a period and space (e.g., "1. ", "2. ", "3. ")
- Each point should be clear, specific, and concise (1-2 sentences max)
- Do NOT use bullet points (-, •, *), ONLY use numbered format (1., 2., 3., etc.)
- Do NOT add headers like "Key Points:" or "Here are the key points:"
- Do NOT add any introductory text or conclusion
- Write all points in {lang_name} language
- Ensure proper line breaks between points (one blank line is acceptable but not required)

CRITICAL SEMANTIC PRESERVATION REQUIREMENTS:
- PRESERVE ALL FACTS, NUMBERS, DATES, NAMES, AND SPECIFIC DETAILS EXACTLY as they appear in the transcript
- Do NOT simplify, omit, or change any factual information
- Do NOT add information that is not in the transcript
- Maintain the same level of detail and emphasis for each point
- Ensure each point can be translated to other languages while maintaining identical meaning
- Include specific numbers, dates, and names ONLY when they are explicitly mentioned in the transcript

VALIDATION CHECK:
Before writing each key point, verify that the information is explicitly mentioned in the transcript below. If you cannot find it in the transcript, DO NOT include it as a point.

REQUIRED OUTPUT FORMAT (follow this exactly):
1. First key point here (with specific details, numbers, dates if mentioned in transcript)
2. Second key point here (preserving all factual information from transcript)
3. Third key point here (maintaining semantic accuracy, no additions)
4. Fourth key point here (extracted directly from transcript)
5. Fifth key point here (no additional information)
6. Sixth key point here (only what is explicitly stated)
7. Seventh key point here (complete the list with exactly 7 points)

IMPORTANT: Output ONLY the numbered list (1. through 7.), nothing else. No headers, no explanations, no bullet points.

Transcript:
{text}

Key Points (in {lang_name}, formatted as a list, preserving all facts and details, using ONLY information from the transcript above):

CRITICAL: Output format must be EXACTLY:
1. First point text here
2. Second point text here
3. Third point text here
4. Fourth point text here
5. Fifth point text here
6. Sixth point text here
7. Seventh point text here

Do NOT include any headers, introductions, or explanations. Start directly with "1. " and end with "7. "."""
    
    def _remove_hallucinations(self, text: str, original_transcript: str) -> str:
        """
        Remove common hallucination patterns from generated text
        
        Args:
            text: Generated text (summary or key points)
            original_transcript: Original transcript text for validation
            
        Returns:
            Text with hallucination patterns removed
        """
        if not text or not original_transcript:
            return text
        
        import re
        
        # Common hallucination phrases that indicate added information
        hallucination_patterns = [
            r'as we all know',
            r'it is well known',
            r'it is common knowledge',
            r'obviously',
            r'clearly',
            r'as observed by everyone',
            r'we have all observed',
            r'everyone has observed',
            r'as everyone can see',
            r'it is evident that',
            r'it is clear that',
            r'undoubtedly',
            r'certainly',
            r'without a doubt',
            r'as expected',
            r'as usual',
            r'typically',
            r'generally',
            r'usually',
            r'in general',
            r'commonly',
            r'as is well documented',
            r'as history shows',
            r'as tradition dictates',
        ]
        
        # Split text into sentences
        sentences = re.split(r'[.!?]\s+', text)
        filtered_sentences = []
        original_lower = original_transcript.lower()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check for hallucination phrases
            has_hallucination_phrase = False
            for pattern in hallucination_patterns:
                if re.search(pattern, sentence.lower()):
                    has_hallucination_phrase = True
                    break
            
            # If sentence has hallucination phrase, check if content is in transcript
            if has_hallucination_phrase:
                # Extract core content (remove hallucination phrase)
                core_content = sentence
                for pattern in hallucination_patterns:
                    core_content = re.sub(pattern, '', core_content, flags=re.IGNORECASE)
                core_content = core_content.strip()
                
                # Check if core content is in transcript
                if core_content and core_content.lower() not in original_lower:
                    # Skip this sentence - likely hallucination
                    continue
            
            # Check if sentence contains information not in transcript
            # Extract key words from sentence
            sentence_words = set(re.findall(r'\b\w+\b', sentence.lower()))
            # Extract key words from transcript
            transcript_words = set(re.findall(r'\b\w+\b', original_lower))
            
            # If sentence has many unique words not in transcript, it might be hallucination
            unique_words = sentence_words - transcript_words
            # Filter out common words (articles, prepositions, etc.)
            common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
            unique_words = unique_words - common_words
            
            # If too many unique words, sentence might be hallucination
            if len(unique_words) > len(sentence_words) * 0.5:  # More than 50% unique words
                # Check if any key content words are in transcript
                key_words = [w for w in sentence_words if len(w) > 4]  # Words longer than 4 chars
                matching_key_words = [w for w in key_words if w in transcript_words]
                
                if len(matching_key_words) < len(key_words) * 0.3:  # Less than 30% key words match
                    # Likely hallucination - skip
                    continue
            
            filtered_sentences.append(sentence)
        
        # Rejoin sentences
        result = '. '.join(filtered_sentences)
        if result and not result.endswith(('.', '!', '?')):
            result += '.'
        
        return result if result else text
    
    def _format_key_points(self, text: str) -> str:
        """
        Format key points text to ensure perfect list formatting
        
        Args:
            text: Raw key points text from LLM
            
        Returns:
            Formatted key points text with consistent numbering (1. through 7.)
        """
        if not text:
            return text
        
        import re
        
        # Remove all common headers, prefixes, and introductory text
        text = re.sub(r'^(Key Points|Points|Main Points|Summary|Key Takeaways|Takeaways)[:：]?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'^(Here are|The following|Below are|These are)[:：]?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        text = re.sub(r'^(The|These|Following)[:：]?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Split by lines and process
        lines = text.split('\n')
        formatted_points = []
        seen_numbers = set()  # Track numbers to avoid duplicates
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            # Skip empty lines
            if not line or len(line) < 3:
                continue
            
            # Skip header lines (standalone headers)
            if re.match(r'^(Key Points|Points|Summary|Main Points|Takeaways|Conclusion|Here are|The following|Below are)[:：]?\s*$', line, re.IGNORECASE):
                continue
            
            # Remove leading/trailing formatting artifacts
            line = re.sub(r'^[:\-–—•\*\s]+', '', line)
            line = re.sub(r'[:\-–—•\*\s]+$', '', line)
            line = line.strip()
            
            if not line:
                continue
            
            # Extract point text from various formats
            point_text = None
            point_number = None
            
            # Pattern 1: Numbered list (1., 2., 3., etc.)
            numbered_match = re.match(r'^(\d+)[\.\)]\s*(.+)$', line)
            if numbered_match:
                point_number = int(numbered_match.group(1))
                point_text = numbered_match.group(2).strip()
            
            # Pattern 2: Number without period/parenthesis (1 text)
            elif re.match(r'^\d+\s+', line):
                parts = re.split(r'^\d+\s+', line, maxsplit=1)
                if len(parts) == 2:
                    point_number = int(re.match(r'^\d+', line).group())
                    point_text = parts[1].strip()
            
            # Pattern 3: Bullet points (-, •, *, etc.)
            elif re.match(r'^[-•*▪▫◦‣⁃]\s+', line):
                point_text = re.sub(r'^[-•*▪▫◦‣⁃]\s+', '', line).strip()
            
            # Pattern 4: Plain text (no numbering/bullet) - treat as continuation or new point
            else:
                # Check if it's a header
                if not re.match(r'^(Key Points|Points|Summary|Main Points|Takeaways|Conclusion|Here are|The following|Below are)', line, re.IGNORECASE):
                    point_text = line.strip()
                    # Remove trailing colons/dashes
                    point_text = re.sub(r'[:：\-–—]+$', '', point_text).strip()
            
            # Process the extracted point text
            if point_text and len(point_text) > 3:
                # Clean up the point text
                point_text = re.sub(r'\s+', ' ', point_text)  # Normalize whitespace
                point_text = point_text.strip()
                
                # Remove any nested numbering/bullets from the text
                point_text = re.sub(r'^\d+[\.\)]\s*', '', point_text)
                point_text = re.sub(r'^[-•*]\s*', '', point_text)
                point_text = point_text.strip()
                
                # Remove trailing punctuation artifacts
                point_text = re.sub(r'[:\-–—•\*]+$', '', point_text).strip()
                
                # Only add if we have meaningful content
                if point_text and len(point_text) > 3:
                    # Use the original number if valid, otherwise assign sequentially
                    if point_number and 1 <= point_number <= 20 and point_number not in seen_numbers:
                        seen_numbers.add(point_number)
                        formatted_points.append((point_number, point_text))
                    else:
                        # Assign next available number
                        next_num = len(formatted_points) + 1
                        formatted_points.append((next_num, point_text))
        
        # Sort by number and create final list
        if formatted_points:
            # Sort by number (if numbers were extracted)
            formatted_points.sort(key=lambda x: x[0])
            
            # Create clean numbered list
            cleaned_points = []
            for idx, (num, point_text) in enumerate(formatted_points, start=1):
                # Use sequential numbering (1., 2., 3., etc.)
                cleaned_points.append(f"{idx}. {point_text}")
            
            # Limit to 7 points
            if len(cleaned_points) > 7:
                cleaned_points = cleaned_points[:7]
            
            # Ensure we have at least some points
            if cleaned_points:
                return '\n'.join(cleaned_points)
        
        # Fallback: Try to extract sentences as points
        # Remove headers first
        clean_text = re.sub(r'^(Key Points|Points|Summary|Main Points)[:：]?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        clean_text = re.sub(r'^(Here are|The following|Below are)[:：]?\s*', '', clean_text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Split by sentences
        sentences = re.split(r'[.!?]\s+', clean_text)
        sentence_points = []
        for sentence in sentences:
            sentence = sentence.strip()
            # Skip very short sentences and headers
            if (sentence and len(sentence) > 15 and 
                not re.match(r'^(Key Points|Points|Summary|Main Points|Takeaways)', sentence, re.IGNORECASE)):
                sentence_points.append(f"{len(sentence_points) + 1}. {sentence}")
                if len(sentence_points) >= 7:
                    break
        
        if sentence_points:
            return '\n'.join(sentence_points)
        
        # Last resort: Return original text with basic cleanup
        # Remove headers and normalize
        final_text = re.sub(r'^(Key Points|Points|Summary|Main Points)[:：]?\s*', '', text, flags=re.IGNORECASE | re.MULTILINE)
        final_text = re.sub(r'\s+', ' ', final_text).strip()
        
        # If it's a single block, try to split by common delimiters
        if '\n' not in final_text and len(final_text) > 50:
            # Try splitting by periods, semicolons, or commas
            parts = re.split(r'[.;]\s+', final_text)
            if len(parts) > 1:
                numbered_parts = [f"{i+1}. {part.strip()}" for i, part in enumerate(parts[:7]) if part.strip()]
                if numbered_parts:
                    return '\n'.join(numbered_parts)
        
        return final_text if final_text else text
    
    def create_custom_note(
        self,
        user_id: int,
        transcript_id: int,
        content: str,
        language: str
    ) -> Dict[str, Any]:
        """
        Create custom note manually
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID
            content: Note content
            language: Language of note
            
        Returns:
            Dictionary with note data
        """
        return self.storage.save_note(
            user_id=user_id,
            transcript_id=transcript_id,
            content=content,
            language=language,
            note_type='custom'
        )
