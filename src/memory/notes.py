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
            # Generate summary using Groq (deterministic with temperature=0.3)
            response = self.groq_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Low temperature for consistency
                max_tokens=512
            )
            
            summary = response.choices[0].message.content.strip()
            
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
            # Generate key points using Groq (deterministic with temperature=0.3)
            response = self.groq_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # Low temperature for consistency
                max_tokens=512
            )
            
            key_points = response.choices[0].message.content.strip()
            
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

Requirements:
- Summarize the main points and key information
- Keep it concise (2-3 paragraphs)
- Preserve important details
- Write the summary in {lang_name} language

Transcript:
{text}

Summary (in {lang_name}):"""
    
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

CRITICAL FORMATTING REQUIREMENTS:
- Extract EXACTLY 7 main points (no more, no less)
- Format as a numbered list (1., 2., 3., etc.) or bullet points (- or •)
- Each point should be on a new line
- Each point should be clear, specific, and concise (1-2 sentences max)
- Organize points logically (most important first, or chronologically)
- Write all points in {lang_name} language
- Use proper formatting with line breaks between points

Example format:
1. First key point here
2. Second key point here
3. Third key point here

OR

• First key point here
• Second key point here
• Third key point here

Transcript:
{text}

Key Points (in {lang_name}, formatted as a list):"""
    
    def _format_key_points(self, text: str) -> str:
        """
        Format key points text to ensure proper list formatting
        
        Args:
            text: Raw key points text from LLM
            
        Returns:
            Formatted key points text
        """
        if not text:
            return text
        
        lines = text.split('\n')
        formatted_lines = []
        counter = 1
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip headers
            if line.lower().startswith(('key points', 'points', 'summary', 'main points')):
                continue
            
            # Check if already formatted
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                formatted_lines.append(line)
                continue
            elif line.startswith(('-', '•', '*')):
                # Convert bullet to numbered
                formatted_lines.append(f"{counter}. {line[1:].strip()}")
                counter += 1
                continue
            else:
                # Add numbering if not present
                formatted_lines.append(f"{counter}. {line}")
                counter += 1
        
        # If we have formatted lines, return them; otherwise return original
        if formatted_lines:
            return '\n'.join(formatted_lines)
        return text
    
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
