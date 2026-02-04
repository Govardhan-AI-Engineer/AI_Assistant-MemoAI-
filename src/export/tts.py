"""
Text-to-Speech (TTS) module for speech synthesis
Task 4: Export & Output
"""
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from src.core.config import Config
from src.core.exceptions import TranscriptionError


class TTSSynthesizer:
    """Convert translated text to audio using free TTS tools"""
    
    def __init__(self, tts_engine: str = "gtts"):
        """
        Initialize TTS synthesizer
        
        Args:
            tts_engine: TTS engine to use ('gtts' or 'pyttsx3')
        """
        self.tts_engine = tts_engine.lower()
        self.gtts_available = False
        self.pyttsx3_available = False
        
        # Check for gTTS
        try:
            from gtts import gTTS
            self.gtts_available = True
        except ImportError:
            pass
        
        # Check for pyttsx3
        try:
            import pyttsx3
            self.pyttsx3_available = True
        except ImportError:
            pass
        
        if not self.gtts_available and not self.pyttsx3_available:
            raise TranscriptionError(
                "No TTS engine available. Please install:\n"
                "  pip install gtts>=2.4.0\n"
                "  or\n"
                "  pip install pyttsx3>=2.90"
            )
        
        # Use available engine if requested one is not available
        if self.tts_engine == "gtts" and not self.gtts_available:
            if self.pyttsx3_available:
                print("WARNING: gTTS not available, using pyttsx3 instead")
                self.tts_engine = "pyttsx3"
            else:
                raise TranscriptionError("gTTS not available and pyttsx3 also not available")
        elif self.tts_engine == "pyttsx3" and not self.pyttsx3_available:
            if self.gtts_available:
                print("WARNING: pyttsx3 not available, using gTTS instead")
                self.tts_engine = "gtts"
            else:
                raise TranscriptionError("pyttsx3 not available and gTTS also not available")
    
    def synthesize(
        self,
        text: str,
        language: str = "en",
        output_path: Optional[Path] = None,
        output_format: str = "mp3",
        slow: bool = False
    ) -> Path:
        """
        Synthesize text to speech
        
        Args:
            text: Text to synthesize
            language: Language code (e.g., 'en', 'hi', 'te')
            output_path: Optional output file path
            output_format: Output format ('mp3' or 'wav')
            slow: Use slow speech (gTTS only)
            
        Returns:
            Path to generated audio file
        """
        if not text or not text.strip():
            raise TranscriptionError("Text cannot be empty")
        
        if output_path is None:
            base_name = f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            output_path = Config.EXPORTS_DIR / "audio" / f"{base_name}.{output_format}"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # For WAV format, prefer pyttsx3 if available (direct WAV output, no conversion needed)
        if output_format.lower() == "wav" and self.pyttsx3_available:
            return self._synthesize_pyttsx3(text, language, output_path, output_format)
        elif self.tts_engine == "gtts":
            return self._synthesize_gtts(text, language, output_path, output_format, slow)
        else:
            return self._synthesize_pyttsx3(text, language, output_path, output_format)
    
    def _synthesize_gtts(
        self,
        text: str,
        language: str,
        output_path: Path,
        output_format: str,
        slow: bool
    ) -> Path:
        """Synthesize using gTTS"""
        from gtts import gTTS
        import io
        
        try:
            # Create gTTS object
            tts = gTTS(text=text, lang=language, slow=slow)
            
            # Save to file
            if output_format.lower() == "mp3":
                tts.save(str(output_path))
            elif output_format.lower() == "wav":
                # gTTS outputs MP3, need to convert to WAV using ffmpeg
                import tempfile
                import subprocess
                
                # Save to temporary MP3 first
                temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                tts.save(temp_mp3.name)
                temp_mp3.close()
                
                try:
                    # Use ffmpeg directly for conversion (doesn't require audioop/pydub)
                    subprocess.run(
                        ['ffmpeg', '-i', temp_mp3.name, '-y', str(output_path)],
                        check=True,
                        capture_output=True,
                        timeout=30
                    )
                    Path(temp_mp3.name).unlink()
                except FileNotFoundError:
                    Path(temp_mp3.name).unlink()
                    # Fallback to pyttsx3 if available
                    if hasattr(self, 'pyttsx3_available') and self.pyttsx3_available:
                        print("⚠️  ffmpeg not found, falling back to pyttsx3 for direct WAV support")
                        return self._synthesize_pyttsx3(text, language, output_path, output_format)
                    raise TranscriptionError(
                        "ffmpeg not found. Please install ffmpeg:\n"
                        "Windows: Download from https://ffmpeg.org/download.html\n"
                        "Linux: sudo apt-get install ffmpeg\n"
                        "macOS: brew install ffmpeg\n"
                        "Or use MP3 format instead."
                    )
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    Path(temp_mp3.name).unlink()
                    # Fallback to pyttsx3 if available
                    if hasattr(self, 'pyttsx3_available') and self.pyttsx3_available:
                        print("⚠️  WAV conversion with ffmpeg failed, falling back to pyttsx3 for direct WAV support")
                        return self._synthesize_pyttsx3(text, language, output_path, output_format)
                    raise TranscriptionError(f"WAV conversion failed: {str(e)}")
            else:
                raise TranscriptionError(f"Unsupported output format: {output_format}")
            
            return output_path
        except Exception as e:
            raise TranscriptionError(f"gTTS synthesis failed: {str(e)}")
    
    def _synthesize_pyttsx3(
        self,
        text: str,
        language: str,
        output_path: Path,
        output_format: str
    ) -> Path:
        """Synthesize using pyttsx3"""
        import pyttsx3
        
        try:
            # Initialize engine
            engine = pyttsx3.init()
            
            # Set properties (language support is limited in pyttsx3)
            # Note: pyttsx3 uses system TTS, language selection may not work for all languages
            try:
                voices = engine.getProperty('voices')
                # Try to find voice matching language (basic implementation)
                # This is a simplified version - full language support requires more complex logic
                if voices:
                    engine.setProperty('voice', voices[0].id)
            except:
                pass
            
            # Set speech rate and volume
            engine.setProperty('rate', 150)  # Speed of speech
            engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
            
            # Save to file
            if output_format.lower() == "wav":
                engine.save_to_file(text, str(output_path))
                engine.runAndWait()
            elif output_format.lower() == "mp3":
                # pyttsx3 outputs WAV, need to convert to MP3 using ffmpeg
                import tempfile
                import subprocess
                
                # Save to temporary WAV first
                temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
                temp_wav_path = temp_wav.name
                temp_wav.close()
                
                engine.save_to_file(text, temp_wav_path)
                engine.runAndWait()
                
                try:
                    # Convert WAV to MP3 using ffmpeg (doesn't require audioop/pydub)
                    subprocess.run(
                        ['ffmpeg', '-i', temp_wav_path, '-y', str(output_path)],
                        check=True,
                        capture_output=True,
                        timeout=30
                    )
                    Path(temp_wav_path).unlink()
                except FileNotFoundError:
                    Path(temp_wav_path).unlink()
                    raise TranscriptionError(
                        "ffmpeg not found. Please install ffmpeg:\n"
                        "Windows: Download from https://ffmpeg.org/download.html\n"
                        "Linux: sudo apt-get install ffmpeg\n"
                        "macOS: brew install ffmpeg\n"
                        "Or use WAV format instead (pyttsx3 supports WAV directly)."
                    )
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
                    Path(temp_wav_path).unlink()
                    raise TranscriptionError(f"MP3 conversion failed: {str(e)}")
            else:
                raise TranscriptionError(f"Unsupported output format: {output_format}")
            
            return output_path
        except Exception as e:
            raise TranscriptionError(f"pyttsx3 synthesis failed: {str(e)}")
    
    def synthesize_paragraphs(
        self,
        paragraphs: List[Dict],
        language: str = "en",
        base_name: Optional[str] = None,
        output_format: str = "mp3",
        per_paragraph: bool = True
    ) -> List[Path]:
        """
        Synthesize multiple paragraphs to audio
        
        Args:
            paragraphs: List of paragraph dictionaries with 'text' key
            language: Language code
            base_name: Base name for output files
            output_format: Output format ('mp3' or 'wav')
            per_paragraph: If True, create one file per paragraph; if False, create single file
            
        Returns:
            List of paths to generated audio files
        """
        if not paragraphs:
            raise TranscriptionError("No paragraphs provided")
        
        if base_name is None:
            base_name = f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        output_files = []
        
        if per_paragraph:
            # Create one file per paragraph
            for idx, para in enumerate(paragraphs):
                para_text = para.get('translated_text', para.get('text', ''))
                if not para_text.strip():
                    continue
                
                output_path = Config.EXPORTS_DIR / "audio" / f"{base_name}_para_{idx+1}.{output_format}"
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                audio_file = self.synthesize(
                    para_text,
                    language=language,
                    output_path=output_path,
                    output_format=output_format
                )
                output_files.append(audio_file)
        else:
            # Create single file with all paragraphs
            all_text = '\n\n'.join([
                para.get('translated_text', para.get('text', ''))
                for para in paragraphs
                if para.get('translated_text', para.get('text', ''))
            ])
            
            output_path = Config.EXPORTS_DIR / "audio" / f"{base_name}.{output_format}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            audio_file = self.synthesize(
                all_text,
                language=language,
                output_path=output_path,
                output_format=output_format
            )
            output_files.append(audio_file)
        
        return output_files
    
    def synthesize_transcription(
        self,
        transcription_data: Dict,
        language: str = "en",
        base_name: Optional[str] = None,
        source_file: Optional[Path] = None,
        translated_text: Optional[str] = None,
        translated_paragraphs: Optional[List[Dict]] = None,
        output_format: str = "mp3",
        per_paragraph: bool = False
    ) -> List[Path]:
        """
        Synthesize transcription or translation to audio
        
        Args:
            transcription_data: Transcription result dictionary
            language: Language code for TTS
            base_name: Base name for output files
            source_file: Original source file (for naming)
            translated_text: Optional translated text to synthesize
            translated_paragraphs: Optional translated paragraphs
            output_format: Output format ('mp3' or 'wav')
            per_paragraph: If True, create one file per paragraph
            
        Returns:
            List of paths to generated audio files
        """
        if base_name is None:
            if source_file:
                base_name = source_file.stem
            else:
                base_name = f"tts_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Determine what to synthesize
        if translated_paragraphs and per_paragraph:
            return self.synthesize_paragraphs(
                translated_paragraphs,
                language=language,
                base_name=base_name,
                output_format=output_format,
                per_paragraph=True
            )
        elif translated_text:
            # Synthesize full translated text
            output_path = Config.EXPORTS_DIR / "audio" / f"{base_name}.{output_format}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return [self.synthesize(
                translated_text,
                language=language,
                output_path=output_path,
                output_format=output_format
            )]
        else:
            # Synthesize original text
            original_text = transcription_data.get('text', '')
            if not original_text:
                raise TranscriptionError("No text found in transcription data")
            
            output_path = Config.EXPORTS_DIR / "audio" / f"{base_name}.{output_format}"
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return [self.synthesize(
                original_text,
                language=language,
                output_path=output_path,
                output_format=output_format
            )]
