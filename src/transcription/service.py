"""
Main transcription service interface
"""
from pathlib import Path
from typing import Dict, Optional
from src.transcription.transcriber import Transcriber
from src.transcription.file_handler import TranscriptionFileHandler
from src.core.config import Config
from src.core.exceptions import TranscriptionError


class TranscriptionService:
    """Main service for transcription operations"""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize transcription service
        
        Args:
            model_name: Whisper model name (default from config)
        """
        self.transcriber = Transcriber(model_name=model_name)
        self.file_handler = TranscriptionFileHandler()
    
    def transcribe(
        self,
        file_path: Path,
        language: Optional[str] = None,
        save_result: bool = True,
        paragraph_format: bool = False,
        words_per_paragraph: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict:
        """
        Transcribe audio/video file
        
        Args:
            file_path: Path to audio/video file
            language: Language code (auto-detect if None)
            save_result: Whether to save transcription to file
            paragraph_format: Whether to format into paragraphs
            words_per_paragraph: Words per paragraph (if paragraph_format=True)
            
        Returns:
            Transcription result dictionary
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise TranscriptionError(f"File not found: {file_path}")
        
        # Perform transcription
        if paragraph_format:
            result = self.transcriber.transcribe_with_paragraphs(
                file_path,
                words_per_paragraph=words_per_paragraph,
                language=language,
                temperature=temperature
            )
        else:
            result = self.transcriber.transcribe_file(
                file_path,
                language=language,
                temperature=temperature
            )
        
        # Save if requested
        if save_result:
            saved_path = self.file_handler.save_transcription(
                result,
                source_file=file_path
            )
            result['saved_path'] = str(saved_path)
            
            # Also save text-only version
            text_path = self.file_handler.save_text_only(
                result['text'],
                source_file=file_path
            )
            result['text_file_path'] = str(text_path)
        
        return result
    
    def get_supported_formats(self) -> Dict:
        """Get list of supported file formats"""
        from src.transcription.audio_extractor import AudioExtractor
        return {
            'video': list(AudioExtractor.SUPPORTED_VIDEO_FORMATS),
            'audio': list(AudioExtractor.SUPPORTED_AUDIO_FORMATS)
        }
