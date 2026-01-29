"""
Main transcription service interface
Task 1 & 2: Core Transcription + Online Media Transcription
"""
from pathlib import Path
from typing import Dict, Optional
import tempfile
import re
from src.transcription.transcriber import Transcriber
from src.transcription.file_handler import TranscriptionFileHandler
from src.transcription.url_handler import URLHandler
from src.transcription.subtitle_parser import SubtitleParser
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
        self.url_handler = URLHandler()
        self.subtitle_parser = SubtitleParser()
    
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
        Transcribe audio/video file or URL
        
        Args:
            file_path: Path to audio/video file or URL string
            language: Language code (auto-detect if None)
            save_result: Whether to save transcription to file
            paragraph_format: Whether to format into paragraphs
            words_per_paragraph: Words per paragraph (if paragraph_format=True)
            temperature: Temperature for transcription
            
        Returns:
            Transcription result dictionary
        """
        input_str = str(file_path)
        
        # Check if input is a URL
        if self.url_handler.is_url(input_str):
            return self.transcribe_url(
                url=input_str,
                language=language,
                save_result=save_result,
                paragraph_format=paragraph_format,
                words_per_paragraph=words_per_paragraph,
                temperature=temperature
            )
        
        # Check if input is a subtitle file
        file_path = Path(file_path)
        if self.subtitle_parser.is_subtitle_file(file_path):
            # Subtitle files don't need transcription, just parsing
            # This is for translation-only workflow
            result = self.subtitle_parser.parse_subtitle(file_path)
            
            # Save if requested
            if save_result:
                saved_path = self.file_handler.save_transcription(
                    result,
                    source_file=file_path
                )
                result['saved_path'] = str(saved_path)
                
                text_path = self.file_handler.save_text_only(
                    result['text'],
                    source_file=file_path
                )
                result['text_file_path'] = str(text_path)
            
            return result
        
        # Regular file transcription (Task 1)
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
    
    def transcribe_url(
        self,
        url: str,
        language: Optional[str] = None,
        save_result: bool = True,
        paragraph_format: bool = False,
        words_per_paragraph: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict:
        """
        Transcribe media from URL (YouTube, podcast, etc.)
        
        Args:
            url: Media URL
            language: Language code (auto-detect if None)
            save_result: Whether to save transcription to file
            paragraph_format: Whether to format into paragraphs
            words_per_paragraph: Words per paragraph
            temperature: Temperature for transcription
            
        Returns:
            Transcription result dictionary
        """
        # Download media from URL
        print(f"Downloading media from URL: {url}")
        download_result = self.url_handler.download_media(url)
        audio_path = download_result['audio_path']
        metadata = download_result.get('metadata', {})
        
        try:
            # Auto-upgrade model based on language (specified or detected)
            current_model = self.transcriber.model_name
            
            if language == 'te' and current_model in ['tiny', 'base', 'small', 'medium']:
                # Telugu specified - upgrade to large model
                print(f"\n⚠️  Telugu language specified - Auto-upgrading from '{current_model}' to 'large' model")
                print(f"   (Large model ensures correct Telugu script without repetition)")
                self.transcriber.reload_model('large')
            elif language and language in ['hi', 'ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa', 'or', 'as'] and current_model in ['tiny', 'base', 'small']:
                # Other Indian languages specified - upgrade to medium model for strong transcription
                print(f"\n⚠️  {language.upper()} language specified - Auto-upgrading from '{current_model}' to 'medium' model")
                print(f"   (Medium model ensures strong transcription quality)")
                self.transcriber.reload_model('medium')
            elif not language:
                # Auto-detection - do a quick language detection first
                print("Auto-detecting language from downloaded audio...")
                quick_result = self.transcriber.model.transcribe(
                    str(audio_path),
                    task="transcribe",
                    language=None,
                    verbose=False
                )
                detected_lang = quick_result.get('language', 'unknown')
                print(f"Detected language: {detected_lang}")
                
                # Auto-upgrade model based on detected language
                if detected_lang == 'te' and current_model in ['tiny', 'base', 'small', 'medium']:
                    print(f"\n⚠️  Telugu detected - Auto-upgrading from '{current_model}' to 'large' model")
                    print(f"   (Large model ensures correct Telugu script without repetition)")
                    self.transcriber.reload_model('large')
                elif detected_lang in ['hi', 'ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa', 'or', 'as'] and current_model in ['tiny', 'base', 'small']:
                    # Other Indian languages benefit from medium model for strong transcription
                    print(f"\n⚠️  {detected_lang.upper()} detected - Auto-upgrading from '{current_model}' to 'medium' model")
                    print(f"   (Medium model ensures strong transcription quality)")
                    self.transcriber.reload_model('medium')
                
                # Pass detected language to transcriber to skip redundant auto-detection
                language = detected_lang
            
            # Transcribe the downloaded audio
            if paragraph_format:
                result = self.transcriber.transcribe_with_paragraphs(
                    audio_path,
                    words_per_paragraph=words_per_paragraph,
                    language=language,
                    temperature=temperature
                )
            else:
                result = self.transcriber.transcribe_file(
                    audio_path,
                    language=language,
                    temperature=temperature
                )
            
            # Add URL metadata
            result['metadata'] = {
                **result.get('metadata', {}),
                **metadata,
                'source_url': url
            }
            
            # Save if requested
            if save_result:
                # Use URL title for filename
                source_name = metadata.get('title', 'url_media')
                # Clean filename
                safe_name = re.sub(r'[^\w\s-]', '', source_name).strip()
                safe_name = re.sub(r'[-\s]+', '-', safe_name)
                
                # Create a Path object for the source (for naming)
                source_path = Path(safe_name)
                
                saved_path = self.file_handler.save_transcription(
                    result,
                    source_file=source_path
                )
                result['saved_path'] = str(saved_path)
                
                text_path = self.file_handler.save_text_only(
                    result['text'],
                    source_file=source_path
                )
                result['text_file_path'] = str(text_path)
            
            return result
            
        finally:
            # Clean up temporary downloaded file
            try:
                if audio_path.exists() and str(audio_path).startswith(str(tempfile.gettempdir())):
                    audio_path.unlink()
            except Exception:
                pass  # Ignore cleanup errors
    
    def get_supported_formats(self) -> Dict:
        """Get list of supported file formats"""
        from src.transcription.audio_extractor import AudioExtractor
        return {
            'video': list(AudioExtractor.SUPPORTED_VIDEO_FORMATS),
            'audio': list(AudioExtractor.SUPPORTED_AUDIO_FORMATS),
            'subtitles': ['.srt', '.vtt'],
            'urls': ['youtube', 'podcast', 'direct_media']
        }
