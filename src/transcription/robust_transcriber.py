"""
Robust transcription pipeline with preprocessing, validation, and retry logic
"""
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.core.config import Config
from src.core.exceptions import TranscriptionError
from src.transcription.audio_extractor import AudioExtractor
from src.transcription.audio_preprocessor import AudioPreprocessor
from src.transcription.audio_validator import AudioValidator
from src.transcription.quality_validator import QualityValidator
from src.transcription.model_selector import ModelSelector
from src.transcription.transcriber import Transcriber


class RobustTranscriber:
    """
    Robust, language-agnostic transcription pipeline with:
    - Audio preprocessing (noise reduction, normalization, channel fixing)
    - Audio validation (corruption detection)
    - Intelligent model selection
    - Output quality validation
    - Automatic retry with fallback models
    """
    
    MAX_RETRIES = 3  # Maximum retry attempts
    
    def __init__(self, initial_model: Optional[str] = None):
        """
        Initialize robust transcriber
        
        Args:
            initial_model: Initial Whisper model to use (default from config)
        """
        self.initial_model = initial_model or Config.WHISPER_MODEL
        self.transcriber = None
        self._initialize_transcriber()
    
    def _initialize_transcriber(self, model_name: Optional[str] = None):
        """Initialize or reload transcriber with specified model"""
        model = model_name or self.initial_model
        if self.transcriber is None or self.transcriber.model_name != model:
            if self.transcriber is not None:
                # Clean up old model
                del self.transcriber
                import gc
                gc.collect()
            self.transcriber = Transcriber(model_name=model)
    
    def transcribe(
        self,
        file_path: Path,
        language: Optional[str] = None,
        task: str = "transcribe",
        temperature: Optional[float] = None,
        enable_preprocessing: bool = True,
        enable_validation: bool = True,
        force_model: Optional[str] = None
    ) -> Dict:
        """
        Robust transcription with full pipeline
        
        Args:
            file_path: Path to audio/video file
            language: Language code (auto-detect if None)
            task: 'transcribe' or 'translate'
            temperature: Temperature for transcription
            enable_preprocessing: Enable audio preprocessing
            enable_validation: Enable audio and output validation
            force_model: Force specific model (overrides intelligent selection)
            
        Returns:
            Transcription result dictionary with quality metrics
        """
        if not file_path.exists():
            raise TranscriptionError(f"File not found: {file_path}")
        
        # Step 1: Extract audio if needed
        audio_path = file_path
        temp_files = []
        
        try:
            if AudioExtractor.is_video_file(file_path):
                print(f"📹 Extracting audio from video: {file_path.name}")
                temp_audio = AudioExtractor.extract_audio(file_path)
                audio_path = temp_audio
                temp_files.append(temp_audio)
            elif not AudioExtractor.is_audio_file(file_path):
                raise TranscriptionError(f"Unsupported file format: {file_path.suffix}")
            
            # Step 2: Validate audio file
            if enable_validation:
                print("🔍 Validating audio file...")
                is_valid, validation_report = AudioValidator.validate(audio_path)
                
                if not is_valid:
                    errors = validation_report.get('errors', [])
                    raise TranscriptionError(
                        f"Audio validation failed: {'; '.join(errors)}"
                    )
                
                warnings = validation_report.get('warnings', [])
                if warnings:
                    for warning in warnings:
                        print(f"⚠️  {warning}")
                
                metadata = validation_report.get('metadata', {})
                duration = metadata.get('duration', 0)
                audio_quality_info = AudioPreprocessor.detect_audio_quality(audio_path)
                estimated_quality = audio_quality_info.get('estimated_quality', 'medium')
            else:
                duration = 0
                estimated_quality = 'medium'
                metadata = {}
            
            # Step 3: Smart preprocessing (optimized for speed while maintaining quality)
            preprocessed_audio = audio_path
            if enable_preprocessing:
                # Check audio quality first to optimize preprocessing
                try:
                    quality_info = AudioPreprocessor.detect_audio_quality(audio_path)
                    estimated_quality = quality_info.get('estimated_quality', 'medium')
                    quality_score = quality_info.get('quality_score', 0)
                    
                    # For very high quality audio (score >= 5), skip heavy noise reduction
                    # but still do normalization and channel fix for consistency
                    if estimated_quality == 'high' and quality_score >= 5:
                        print(f"🔧 High-quality audio detected (score: {quality_score}), using optimized preprocessing...")
                        preprocessed_audio, preprocess_metadata = AudioPreprocessor.preprocess(
                            audio_path,
                            enable_noise_reduction=False,  # Skip heavy noise reduction for high-quality audio
                            enable_normalization=True,  # Keep normalization for consistency
                            enable_channel_fix=True  # Keep channel fix for compatibility
                        )
                    else:
                        # For medium/low quality, use full preprocessing
                        print("🔧 Preprocessing audio (noise reduction, normalization, channel fixing)...")
                        preprocessed_audio, preprocess_metadata = AudioPreprocessor.preprocess(
                            audio_path,
                            enable_noise_reduction=True,
                            enable_normalization=True,
                            enable_channel_fix=True
                        )
                    
                    # If preprocessing created a new file, track it for cleanup
                    if preprocessed_audio != audio_path:
                        temp_files.append(preprocessed_audio)
                    
                    print("✅ Audio preprocessing completed")
                except Exception as e:
                    print(f"⚠️  Preprocessing failed, using original audio: {e}")
                    preprocessed_audio = audio_path
            
            # Step 4: Intelligent model selection
            print("🤖 Selecting optimal model...")
            selected_model, selection_reason = ModelSelector.select_model(
                language=language,
                audio_quality=estimated_quality,
                duration=duration,
                current_model=self.transcriber.model_name if self.transcriber else None,
                force_model=force_model
            )
            
            print(f"📊 Model selection: {selection_reason['reason']}")
            
            # Load selected model if different
            if self.transcriber.model_name != selected_model:
                print(f"🔄 Loading model: {selected_model}")
                self._initialize_transcriber(selected_model)
            
            # Step 5: Transcription with retry logic
            result = None
            last_error = None
            attempts = 0
            
            while attempts < self.MAX_RETRIES:
                attempts += 1
                current_model = self.transcriber.model_name
                
                try:
                    print(f"🎤 Transcribing (attempt {attempts}/{self.MAX_RETRIES}) with {current_model} model...")
                    
                    # Perform transcription
                    result = self.transcriber.transcribe_file(
                        preprocessed_audio,
                        language=language,
                        task=task,
                        temperature=temperature
                    )
                    
                    # Step 6: Validate output quality
                    if enable_validation:
                        print("🔍 Validating transcription quality...")
                        transcribed_text = result.get('text', '')
                        compression_ratio = None
                        
                        # Extract compression ratio from segments if available
                        segments = result.get('segments', [])
                        if segments:
                            compression_ratio = segments[0].get('compression_ratio')
                        
                        is_valid, quality_report = QualityValidator.validate(
                            text=transcribed_text,
                            language=language or result.get('language'),
                            compression_ratio=compression_ratio,
                            segments=segments
                        )
                        
                        # Add quality report to result
                        result['quality_report'] = quality_report
                        
                        # Speed optimization: Skip retries if quality is already excellent (>= 85)
                        # This maintains quality while improving speed for good results
                        quality_score = quality_report.get('quality_score', 100)
                        if quality_score >= 85 and is_valid:
                            print(f"✅ Excellent quality score ({quality_score}), skipping retries")
                            break  # Exit retry loop early - quality is already excellent
                        
                        # Check if retry is needed
                        if not is_valid or quality_score < 70:
                            should_retry, next_model = ModelSelector.should_retry_with_larger_model(
                                quality_report,
                                current_model,
                                language or result.get('language')
                            )
                            
                            if should_retry and next_model and attempts < self.MAX_RETRIES:
                                print(f"⚠️  Quality issues detected. Retrying with {next_model} model...")
                                print(f"   Issues: {quality_report.get('warnings', [])}")
                                
                                # Upgrade model and retry
                                self._initialize_transcriber(next_model)
                                continue
                            elif not is_valid:
                                # Critical errors, but can't retry
                                errors = quality_report.get('errors', [])
                                warnings = quality_report.get('warnings', [])
                                print(f"❌ Transcription quality validation failed:")
                                for err in errors:
                                    print(f"   - {err}")
                                for warn in warnings:
                                    print(f"   ⚠️  {warn}")
                                
                                # Still return result, but with warnings
                                result['quality_warnings'] = warnings
                                result['quality_errors'] = errors
                        else:
                            print(f"✅ Transcription quality validated (score: {quality_report.get('quality_score', 100)})")
                    
                    # Success - break retry loop
                    break
                    
                except Exception as e:
                    last_error = e
                    print(f"❌ Transcription attempt {attempts} failed: {str(e)}")
                    
                    # Try with larger model if available
                    if attempts < self.MAX_RETRIES:
                        next_model = ModelSelector.get_fallback_model(
                            current_model,
                            language
                        )
                        
                        if next_model != current_model:
                            print(f"🔄 Retrying with {next_model} model...")
                            self._initialize_transcriber(next_model)
                        else:
                            # Already at largest model, can't retry
                            break
                    else:
                        # Out of retries
                        break
            
            # Check if we have a result
            if result is None:
                if last_error:
                    raise TranscriptionError(
                        f"Transcription failed after {attempts} attempts: {str(last_error)}"
                    )
                else:
                    raise TranscriptionError("Transcription failed: No result returned")
            
            # Add metadata
            result['metadata'] = {
                **result.get('metadata', {}),
                'model_used': self.transcriber.model_name,
                'preprocessing_applied': enable_preprocessing and preprocessed_audio != audio_path,
                'validation_applied': enable_validation,
                'audio_duration': duration,
                'audio_quality': estimated_quality,
                'attempts': attempts
            }
            
            return result
            
        finally:
            # Clean up temporary files
            for temp_file in temp_files:
                if temp_file.exists() and str(temp_file).startswith(str(tempfile.gettempdir())):
                    try:
                        temp_file.unlink()
                    except Exception:
                        pass
    
    def transcribe_with_paragraphs(
        self,
        file_path: Path,
        words_per_paragraph: Optional[int] = None,
        language: Optional[str] = None,
        temperature: Optional[float] = None,
        enable_preprocessing: bool = True,
        enable_validation: bool = True,
        force_model: Optional[str] = None
    ) -> Dict:
        """
        Transcribe and format into paragraphs with robust pipeline
        
        Args:
            file_path: Path to audio/video file
            words_per_paragraph: Target words per paragraph
            language: Language code (auto-detect if None)
            temperature: Temperature for transcription
            enable_preprocessing: Enable audio preprocessing
            enable_validation: Enable validation
            force_model: Force specific model
            
        Returns:
            Dictionary with transcription and paragraphs
        """
        words_per_paragraph = words_per_paragraph or Config.PARAGRAPH_WORD_COUNT
        
        # Get transcription
        result = self.transcribe(
            file_path,
            language=language,
            temperature=temperature,
            enable_preprocessing=enable_preprocessing,
            enable_validation=enable_validation,
            force_model=force_model
        )
        
        # Format into paragraphs
        segments = result.get('segments', [])
        paragraphs = self._format_paragraphs(segments, words_per_paragraph)
        
        return {
            'text': result['text'],
            'language': result['language'],
            'paragraphs': paragraphs,
            'segments': segments,
            'quality_report': result.get('quality_report'),
            'metadata': result.get('metadata', {})
        }
    
    def _format_paragraphs(
        self,
        segments: List[Dict],
        words_per_paragraph: int
    ) -> List[Dict]:
        """Format segments into paragraphs"""
        paragraphs = []
        current_paragraph = {
            'text': '',
            'words': [],
            'start': None,
            'end': None
        }
        
        word_count = 0
        
        for segment in segments:
            segment_text = segment.get('text', '').strip()
            if not segment_text:
                continue
            
            words = segment_text.split()
            segment_start = segment.get('start', 0)
            segment_end = segment.get('end', 0)
            
            if current_paragraph['start'] is None:
                current_paragraph['start'] = segment_start
            
            for word in words:
                current_paragraph['words'].append(word)
                word_count += 1
                
                if word_count >= words_per_paragraph:
                    current_paragraph['text'] = ' '.join(current_paragraph['words'])
                    current_paragraph['end'] = segment_end
                    paragraphs.append(current_paragraph)
                    
                    current_paragraph = {
                        'text': '',
                        'words': [],
                        'start': None,
                        'end': None
                    }
                    word_count = 0
            
            current_paragraph['end'] = segment_end
        
        if current_paragraph['words']:
            current_paragraph['text'] = ' '.join(current_paragraph['words'])
            paragraphs.append(current_paragraph)
        
        return paragraphs
