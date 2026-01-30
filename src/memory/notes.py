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
        model: str = "llama-3.1-8b-instant"
    ) -> Dict[str, Any]:
        """
        Generate canonical summary note from transcript
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID
            transcript_text: Full transcript text
            language: Language of transcript
            model: Groq model to use
            
        Returns:
            Dictionary with note data
        """
        if not self.groq_client:
            raise ValueError("Groq API not available. Set GROQ_API_KEY in .env file")
        
        # Create prompt for summary generation
        prompt = self._create_summary_prompt(transcript_text, language)
        
        try:
            # Generate summary using Groq
            response = self.groq_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=512
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Save note
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
        model: str = "llama-3.1-8b-instant"
    ) -> Dict[str, Any]:
        """
        Generate key points note from transcript
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID
            transcript_text: Full transcript text
            language: Language of transcript
            model: Groq model to use
            
        Returns:
            Dictionary with note data
        """
        if not self.groq_client:
            raise ValueError("Groq API not available. Set GROQ_API_KEY in .env file")
        
        # Create prompt for key points
        prompt = self._create_key_points_prompt(transcript_text, language)
        
        try:
            # Generate key points using Groq
            response = self.groq_client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=512
            )
            
            key_points = response.choices[0].message.content.strip()
            
            # Save note
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
        return f"""Generate a concise summary of the following transcript in {language}.

Requirements:
- Summarize the main points and key information
- Keep it concise (2-3 paragraphs)
- Preserve important details
- Write in the same language as the transcript

Transcript:
{text}

Summary:"""
    
    def _create_key_points_prompt(self, text: str, language: str) -> str:
        """Create prompt for key points generation"""
        return f"""Extract the key points from the following transcript in {language}.

Requirements:
- List 5-10 main points
- Use bullet points or numbered list
- Be specific and concise
- Write in the same language as the transcript

Transcript:
{text}

Key Points:"""
    
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
