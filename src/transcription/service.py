"""
Main transcription service interface
Task 1 & 2: Core Transcription + Online Media Transcription
"""
from pathlib import Path
from typing import Dict, Optional
import tempfile
import re
from src.transcription.transcriber import Transcriber
from src.transcription.robust_transcriber import RobustTranscriber
from src.transcription.file_handler import TranscriptionFileHandler
from src.transcription.url_handler import URLHandler
from src.transcription.subtitle_parser import SubtitleParser
from src.core.config import Config
from src.core.exceptions import TranscriptionError


class TranscriptionService:
    """Main service for transcription operations"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        use_robust_pipeline: bool = True
    ):
        """
        Initialize transcription service
        
        Args:
            model_name: Whisper model name (default from config)
            use_robust_pipeline: Use robust pipeline with preprocessing and validation
        """
        self.use_robust_pipeline = use_robust_pipeline
        if use_robust_pipeline:
            self.transcriber = RobustTranscriber(initial_model=model_name)
            self.legacy_transcriber = None
        else:
            self.transcriber = None
            self.legacy_transcriber = Transcriber(model_name=model_name)
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
        temperature: Optional[float] = None,
        enable_preprocessing: bool = True,
        enable_validation: bool = True,
        force_model: Optional[str] = None
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
        transcriber_to_use = self.transcriber if self.use_robust_pipeline else self.legacy_transcriber
        
        if paragraph_format:
            if self.use_robust_pipeline:
                result = transcriber_to_use.transcribe_with_paragraphs(
                    file_path,
                    words_per_paragraph=words_per_paragraph,
                    language=language,
                    temperature=temperature,
                    enable_preprocessing=enable_preprocessing,
                    enable_validation=enable_validation,
                    force_model=force_model
                )
            else:
                result = transcriber_to_use.transcribe_with_paragraphs(
                    file_path,
                    words_per_paragraph=words_per_paragraph,
                    language=language,
                    temperature=temperature
                )
        else:
            if self.use_robust_pipeline:
                result = transcriber_to_use.transcribe(
                    file_path,
                    language=language,
                    temperature=temperature,
                    enable_preprocessing=enable_preprocessing,
                    enable_validation=enable_validation,
                    force_model=force_model
                )
            else:
                result = transcriber_to_use.transcribe_file(
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
        temperature: Optional[float] = None,
        enable_preprocessing: bool = True,
        enable_validation: bool = True,
        force_model: Optional[str] = None
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
            enable_preprocessing: Enable audio preprocessing
            enable_validation: Enable validation (especially important for downloads)
            force_model: Force specific model
            
        Returns:
            Transcription result dictionary
        """
        # Download media from URL
        print(f"Downloading media from URL: {url}")
        download_result = self.url_handler.download_media(url)
        audio_path = download_result['audio_path']
        metadata = download_result.get('metadata', {})
        
        # Validate downloaded audio (especially important for YouTube Shorts/podcasts)
        if enable_validation:
            from src.transcription.audio_validator import AudioValidator
            print("🔍 Validating downloaded audio...")
            expected_duration = metadata.get('duration')
            is_valid, validation_report = AudioValidator.validate_download_completeness(
                audio_path,
                metadata,
                source=metadata.get('source', 'youtube')
            )
            
            if not is_valid:
                errors = validation_report.get('errors', [])
                raise TranscriptionError(
                    f"Downloaded audio validation failed: {'; '.join(errors)}"
                )
            
            warnings = validation_report.get('warnings', [])
            if warnings:
                for warning in warnings:
                    print(f"⚠️  {warning}")
        
        try:
            transcriber_to_use = self.transcriber if self.use_robust_pipeline else self.legacy_transcriber
            
            # For robust pipeline, model selection is handled automatically
            if not self.use_robust_pipeline:
                # Legacy model upgrade logic (only for non-robust mode)
                current_model = transcriber_to_use.model_name
                
                if language == 'te' and current_model in ['tiny', 'base', 'small', 'medium']:
                    print(f"\n⚠️  Telugu language specified - Auto-upgrading from '{current_model}' to 'large' model")
                    transcriber_to_use.reload_model('large')
                elif language and language in ['hi', 'ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa', 'or', 'as'] and current_model in ['tiny', 'base', 'small']:
                    print(f"\n⚠️  {language.upper()} language specified - Auto-upgrading to 'medium' model")
                    transcriber_to_use.reload_model('medium')
                elif not language:
                    # Quick language detection
                    print("Auto-detecting language from downloaded audio...")
                    quick_result = transcriber_to_use.model.transcribe(
                        str(audio_path),
                        task="transcribe",
                        language=None,
                        verbose=False
                    )
                    detected_lang = quick_result.get('language', 'unknown')
                    print(f"Detected language: {detected_lang}")
                    
                    if detected_lang == 'te' and current_model in ['tiny', 'base', 'small', 'medium']:
                        print(f"\n⚠️  Telugu detected - Auto-upgrading to 'large' model")
                        transcriber_to_use.reload_model('large')
                    elif detected_lang in ['hi', 'ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa', 'or', 'as'] and current_model in ['tiny', 'base', 'small']:
                        print(f"\n⚠️  {detected_lang.upper()} detected - Auto-upgrading to 'medium' model")
                        transcriber_to_use.reload_model('medium')
                    
                    language = detected_lang
            
            # Transcribe the downloaded audio
            if paragraph_format:
                if self.use_robust_pipeline:
                    result = transcriber_to_use.transcribe_with_paragraphs(
                        audio_path,
                        words_per_paragraph=words_per_paragraph,
                        language=language,
                        temperature=temperature,
                        enable_preprocessing=enable_preprocessing,
                        enable_validation=enable_validation,
                        force_model=force_model
                    )
                else:
                    result = transcriber_to_use.transcribe_with_paragraphs(
                        audio_path,
                        words_per_paragraph=words_per_paragraph,
                        language=language,
                        temperature=temperature
                    )
            else:
                if self.use_robust_pipeline:
                    result = transcriber_to_use.transcribe(
                        audio_path,
                        language=language,
                        temperature=temperature,
                        enable_preprocessing=enable_preprocessing,
                        enable_validation=enable_validation,
                        force_model=force_model
                    )
                else:
                    result = transcriber_to_use.transcribe_file(
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
