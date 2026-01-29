"""
Core transcription service using OpenAI Whisper (Free & Open-Source)
Supports all languages with medium model for best accuracy
"""
import whisper
from pathlib import Path
from typing import Dict, List, Optional
from src.core.config import Config
from src.core.exceptions import TranscriptionError
from src.transcription.audio_extractor import AudioExtractor


class Transcriber:
    """Transcription service using OpenAI Whisper (free, open-source) - Universal language support"""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize transcriber with Whisper model
        
        Args:
            model_name: Whisper model name (tiny, base, small, medium, large)
                        Defaults to Config.WHISPER_MODEL
        """
        self.model_name = model_name or Config.WHISPER_MODEL
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load Whisper model"""
        try:
            print(f"Loading Whisper model: {self.model_name}")
            self.model = whisper.load_model(self.model_name)
            print(f"Model {self.model_name} loaded successfully")
        except Exception as e:
            raise TranscriptionError(f"Failed to load Whisper model: {str(e)}")
    
    def reload_model(self, model_name: str):
        """Reload model with different model name (e.g., upgrade from small to medium)"""
        if self.model_name == model_name:
            return  # Already using this model
        
        print(f"Reloading model: {self.model_name} → {model_name}")
        # Free up memory from old model
        if self.model is not None:
            del self.model
            import gc
            gc.collect()
        self.model_name = model_name
        self._load_model()
    
    def transcribe_file(
        self,
        file_path: Path,
        language: Optional[str] = None,
        task: str = "transcribe",
        temperature: Optional[float] = None
    ) -> Dict:
        """
        Transcribe audio/video file - Universal support for all languages
        
        Args:
            file_path: Path to audio/video file
            language: Language code (e.g., 'en', 'es', 'de', 'fr', 'hi', 'te'). Auto-detect if None
            task: 'transcribe' or 'translate'
            temperature: Temperature for transcription (0 = deterministic). Default from config
            
        Returns:
            Dictionary with transcription results
        """
        if not file_path.exists():
            raise TranscriptionError(f"File not found: {file_path}")
        
        # Extract audio if needed
        audio_path = file_path
        temp_audio = None
        
        try:
            if AudioExtractor.is_video_file(file_path):
                print(f"Extracting audio from video: {file_path}")
                temp_audio = AudioExtractor.extract_audio(file_path)
                audio_path = temp_audio
            elif not AudioExtractor.is_audio_file(file_path):
                raise TranscriptionError(f"Unsupported file format: {file_path.suffix}")
            
            # Transcribe with Whisper
            print(f"Transcribing: {audio_path}")
            temp = temperature if temperature is not None else Config.WHISPER_TEMPERATURE
            
            # Universal parameters - optimized for STRONG transcription quality
            # Balanced parameters to prevent repetition while maintaining accuracy
            transcribe_params = {
                'language': language,  # None = auto-detect
                'task': task,
                'verbose': False,
                'temperature': temp,
                # Use conditional text for better context, but with careful thresholds
                'condition_on_previous_text': True,  # Enable for better context
                'beam_size': 5,  # Use beam search for better accuracy (medium/large models handle this well)
                'best_of': 5,  # Try multiple candidates for best result
                'patience': 1.0,
                'compression_ratio_threshold': 2.4,  # Stricter threshold to catch repetition
                'logprob_threshold': -1.0,
                'no_speech_threshold': 0.6,
            }
            
            # For smaller models (tiny/base), use simpler parameters to avoid repetition
            if self.model_name in ['tiny', 'base']:
                transcribe_params['beam_size'] = 1  # Greedy decoding for small models
                transcribe_params['best_of'] = 1
                transcribe_params['condition_on_previous_text'] = False
            
            # Remove best_of - it can cause repetition
            # Only use beam_size=1 (greedy) for better results without repetition
            
            # Language prompts for ALL languages - helps guide transcription
            language_prompts = {
                # Indian languages (script guidance)
                'te': 'తెలుగు',  # Telugu
                'hi': 'हिंदी',  # Hindi
                'ta': 'தமிழ்',  # Tamil
                'kn': 'ಕನ್ನಡ',  # Kannada
                'ml': 'മലയാളം',  # Malayalam
                'gu': 'ગુજરાતી',  # Gujarati
                'pa': 'ਪੰਜਾਬੀ',  # Punjabi
                'bn': 'বাংলা',  # Bengali
                'mr': 'मराठी',  # Marathi
                'or': 'ଓଡ଼ିଆ',  # Odia
                'as': 'অসমীয়া',  # Assamese
                
                # European languages
                'en': 'Hello, this is English.',  # English
                'de': 'Hallo, das ist Deutsch.',  # German
                'fr': 'Bonjour, c\'est le français.',  # French
                'es': 'Hola, esto es español.',  # Spanish
                'it': 'Ciao, questo è italiano.',  # Italian
                'pt': 'Olá, isto é português.',  # Portuguese
                'nl': 'Hallo, dit is Nederlands.',  # Dutch
                'ru': 'Привет, это русский язык.',  # Russian
                'pl': 'Cześć, to jest polski.',  # Polish
                'uk': 'Привіт, це українська мова.',  # Ukrainian
                
                # Asian languages
                'zh': '你好，这是中文。',  # Chinese
                'ja': 'こんにちは、これは日本語です。',  # Japanese
                'ko': '안녕하세요, 이것은 한국어입니다.',  # Korean
                'ar': 'مرحبا، هذا هو العربية.',  # Arabic
                'th': 'สวัสดี นี่คือภาษาไทย',  # Thai
                'vi': 'Xin chào, đây là tiếng Việt.',  # Vietnamese
                
                # Other languages
                'tr': 'Merhaba, bu Türkçe.',  # Turkish
                'he': 'שלום, זה עברית.',  # Hebrew
                'cs': 'Ahoj, toto je čeština.',  # Czech
                'sv': 'Hej, det här är svenska.',  # Swedish
                'no': 'Hei, dette er norsk.',  # Norwegian
                'fi': 'Hei, tämä on suomea.',  # Finnish
                'da': 'Hej, det er dansk.',  # Danish
                'el': 'Γεια σας, αυτό είναι ελληνικά.',  # Greek
                'hu': 'Helló, ez magyar.',  # Hungarian
                'ro': 'Bună, acesta este română.',  # Romanian
            }
            
            # First pass: Auto-detect language if not specified
            if not language:
                print("Auto-detecting language...")
                result = self.model.transcribe(str(audio_path), **transcribe_params)
                detected_lang = result.get('language', 'unknown')
                print(f"Detected language: {detected_lang}")
                
                effective_language = detected_lang
                
                # CRITICAL: If Telugu is detected and we're using small/tiny/base/medium model,
                # reload with large model to prevent repetition (compression_ratio > 7)
                if effective_language == 'te' and self.model_name in ['tiny', 'base', 'small', 'medium']:
                    print(f"\n⚠️  Telugu detected with {self.model_name} model - upgrading to large model")
                    print(f"   (Large model ensures correct Telugu script without repetition)")
                    self.reload_model('large')
                # For Hindi and other Indian languages, upgrade to medium if using smaller models
                elif effective_language in ['hi', 'ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa', 'or', 'as'] and self.model_name in ['tiny', 'base', 'small']:
                    print(f"\n⚠️  {effective_language.upper()} detected with {self.model_name} model - upgrading to medium model")
                    print(f"   (Medium model ensures strong transcription quality)")
                    self.reload_model('medium')
                
                # Re-transcribe with language-specific prompt if available
                # For Telugu, DON'T use initial_prompt - it causes repetition
                if effective_language == 'te':
                    # Telugu: Re-transcribe without initial prompt to prevent repetition
                    print(f"Re-transcribing Telugu with optimized parameters (no initial prompt)")
                    transcribe_params['language'] = effective_language
                    transcribe_params['task'] = 'transcribe'  # Force transcribe
                    # NO initial_prompt for Telugu - it causes repetition
                    result = self.model.transcribe(str(audio_path), **transcribe_params)
                elif effective_language in language_prompts:
                    print(f"Re-transcribing with {effective_language.upper()}-specific guidance")
                    transcribe_params['language'] = effective_language
                    transcribe_params['task'] = 'transcribe'  # Force transcribe
                    transcribe_params['initial_prompt'] = language_prompts[effective_language]
                    result = self.model.transcribe(str(audio_path), **transcribe_params)
                elif effective_language != 'en':
                    # For other languages without prompts, ensure transcribe mode
                    transcribe_params['language'] = effective_language
                    transcribe_params['task'] = 'transcribe'
                    result = self.model.transcribe(str(audio_path), **transcribe_params)
            else:
                # Language was specified (or passed from service.py after detection)
                effective_language = language
                if language != 'en':
                    transcribe_params['task'] = 'transcribe'  # Force transcribe, not translate
                    print(f"Transcribing with language: {language} (transcribe mode)")
                
                # Set language in params for accurate transcription
                transcribe_params['language'] = language
                
                # For Telugu, DON'T use initial_prompt - it causes repetition
                # For other languages, use initial prompt if available
                if language == 'te':
                    # Telugu: No initial prompt to prevent repetition
                    print(f"Using optimized parameters for Telugu (no initial prompt to prevent repetition)")
                elif language in language_prompts:
                    transcribe_params['initial_prompt'] = language_prompts[language]
                    print(f"Using {language.upper()}-specific guidance")
                
                # Single transcription pass with language and prompt (no redundant detection)
                result = self.model.transcribe(str(audio_path), **transcribe_params)
            
            # Post-processing: Validation and quality checks
            detected_lang = result.get('language', 'unknown')
            transcribed_text = result.get('text', '').strip()
            
            # Use effective language (detected or specified) for validation
            effective_language = language if language else detected_lang
            
            # Check for repetition issues
            def has_repetition(text: str, min_repeat: int = 3) -> bool:
                """Check if text has repeating character patterns"""
                if len(text) < 10:
                    return False
                # Check for same character repeated 3+ times consecutively
                for i in range(len(text) - min_repeat):
                    if len(set(text[i:i+min_repeat])) == 1 and text[i] not in [' ', '.', ',', '!', '?']:
                        return True
                # Check for repeating word patterns
                words = text.split()
                if len(words) > 5:
                    for i in range(len(words) - 2):
                        if words[i] == words[i+1] == words[i+2]:
                            return True
                return False
            
            # Check compression ratio
            compression_ratio = 1.0
            if result.get('segments'):
                compression_ratio = result['segments'][0].get('compression_ratio', 1.0)
            
            # Check for repetition - use strict threshold
            # Compression ratio > 2.5 usually indicates repetition
            if has_repetition(transcribed_text) or compression_ratio > 2.5:
                if compression_ratio > 2.5:
                    print(f"\n⚠️  WARNING: Possible repetition detected (compression_ratio: {compression_ratio:.2f})")
                    if compression_ratio > 5.0:
                        print(f"   ❌ CRITICAL: Very high compression ratio indicates severe repetition!")
                        print(f"   This may be caused by:")
                        print(f"   - Model size too small for this language")
                        print(f"   - Initial prompt causing repetition")
                        print(f"   - Audio quality issues")
                        if effective_language == 'te':
                            print(f"   SOLUTION: Telugu requires --model medium or --model large")
                            print(f"   Command: python main.py {file_path.name} --language te --model medium")
                if self.model_name in ['tiny', 'base', 'small']:
                    if effective_language == 'te':
                        print(f"   For Telugu, you MUST use --model medium or --model large")
                    else:
                        print(f"   Consider using --model small or larger for better results")
            
            # Script validation for Indian languages (they have specific scripts)
            # Use effective_language (detected or specified)
            self._validate_indian_language_script(effective_language, transcribed_text, result, file_path)
            
            # General validation: Check if detected language matches requested (if language was specified)
            if language and detected_lang != language:
                print(f"\n⚠️  Warning: Requested language '{language}' but detected '{detected_lang}'")
                print(f"   This may indicate transcription quality issues")
                if self.model_name in ['tiny', 'base', 'small']:
                    print(f"   Consider using --model medium for better accuracy")
            
            return {
                'text': result['text'],
                'language': result.get('language', 'unknown'),
                'segments': result.get('segments', []),
                'full_result': result
            }
            
        except Exception as e:
            raise TranscriptionError(f"Transcription failed: {str(e)}")
        finally:
            # Clean up temp audio file
            if temp_audio and temp_audio.exists():
                try:
                    temp_audio.unlink()
                except Exception:
                    pass
    
    def _validate_indian_language_script(
        self,
        language: Optional[str],
        transcribed_text: str,
        result: Dict,
        file_path: Path
    ):
        """
        Validate script for Indian languages (they have specific scripts)
        For other languages (German, French, etc.), this is not needed as they use standard scripts
        """
        if not language:
            return
        
        # Unicode ranges for Indian language scripts
        script_ranges = {
            'te': (0x0C00, 0x0C7F, 'Telugu'),  # Telugu
            'hi': (0x0900, 0x097F, 'Devanagari'),  # Hindi (Devanagari)
            'ta': (0x0B80, 0x0BFF, 'Tamil'),  # Tamil
            'kn': (0x0C80, 0x0CFF, 'Kannada'),  # Kannada
            'ml': (0x0D00, 0x0D7F, 'Malayalam'),  # Malayalam
            'gu': (0x0A80, 0x0AFF, 'Gujarati'),  # Gujarati
            'pa': (0x0A00, 0x0A7F, 'Gurmukhi'),  # Punjabi (Gurmukhi)
            'bn': (0x0980, 0x09FF, 'Bengali'),  # Bengali
            'mr': (0x0900, 0x097F, 'Devanagari'),  # Marathi (Devanagari)
            'or': (0x0B00, 0x0B7F, 'Odia'),  # Odia
            'as': (0x0980, 0x09FF, 'Assamese'),  # Assamese (same as Bengali)
        }
        
        if language not in script_ranges:
            return  # Not an Indian language, no script validation needed
        
        script_range, script_name = script_ranges[language][:2], script_ranges[language][2]
        
        # Count characters in correct script
        correct_script_count = sum(1 for char in transcribed_text if script_range[0] <= ord(char) <= script_range[1])
        
        # Check for wrong scripts (other Indian scripts)
        wrong_scripts = {
            'te': [(0x0B80, 0x0BFF, 'Tamil'), (0x0900, 0x097F, 'Devanagari')],  # Telugu shouldn't be Tamil or Devanagari
            'hi': [(0x0C00, 0x0C7F, 'Telugu'), (0x0B80, 0x0BFF, 'Tamil')],  # Hindi shouldn't be Telugu or Tamil
            'ta': [(0x0C00, 0x0C7F, 'Telugu'), (0x0900, 0x097F, 'Devanagari')],  # Tamil shouldn't be Telugu or Devanagari
        }
        
        # Check for Roman script (English letters) - common issue for Hindi
        roman_count = sum(1 for char in transcribed_text if char.isascii() and char.isalpha() and char.islower())
        total_alpha = sum(1 for char in transcribed_text if char.isalpha())
        is_mostly_roman = total_alpha > 0 and (roman_count / total_alpha) > 0.3
        
        # Check compression ratio
        compression_ratio = 1.0
        if result.get('segments'):
            compression_ratio = result['segments'][0].get('compression_ratio', 1.0)
        
        has_correct_script = correct_script_count > 0
        
        # Validation for Telugu - CRITICAL: Must output in Telugu script, not Devanagari or Tamil
        if language == 'te':
            telugu_count = correct_script_count
            tamil_count = sum(1 for char in transcribed_text if 0x0B80 <= ord(char) <= 0x0BFF)
            devanagari_count = sum(1 for char in transcribed_text if 0x0900 <= ord(char) <= 0x097F)
            english_count = sum(1 for char in transcribed_text[:200] if char.isascii() and char.isalpha())
            
            # CRITICAL: If no Telugu script found, but Devanagari or Tamil found, it's wrong
            if telugu_count == 0:
                if devanagari_count > 0:
                    print(f"\n❌ ERROR: Telugu audio was transcribed in Devanagari (Hindi) script!")
                    print(f"   Detected: {devanagari_count} Devanagari characters, {telugu_count} Telugu characters")
                    print(f"   Current model: {self.model_name}")
                    raise TranscriptionError(
                        f"Telugu transcription failed: Output is in Devanagari script (Hindi), not Telugu script. "
                        f"Model '{self.model_name}' is not producing correct Telugu script. "
                        f"SOLUTION: Use --model large for Telugu to ensure correct script. "
                        f"Command: python main.py {file_path.name} --language te --model large"
                    )
                elif tamil_count > 0:
                    print(f"\n❌ ERROR: Telugu audio was transcribed in Tamil script!")
                    print(f"   Detected: {tamil_count} Tamil characters, {telugu_count} Telugu characters")
                    print(f"   Current model: {self.model_name}")
                    raise TranscriptionError(
                        f"Telugu transcription failed: Output is in Tamil script, not Telugu script. "
                        f"Model '{self.model_name}' is not producing correct Telugu script. "
                        f"Use --model large for Telugu. "
                        f"Command: python main.py {file_path.name} --language te --model large"
                    )
                elif english_count > 50:
                    print(f"\n❌ ERROR: Telugu audio was transcribed in English!")
                    print(f"   Current model: {self.model_name}")
                    raise TranscriptionError(
                        f"Telugu transcription failed: Output is in English (translated), not Telugu script. "
                        f"Model '{self.model_name}' is translating instead of transcribing. "
                        f"Use --model large for Telugu. "
                        f"Command: python main.py {file_path.name} --language te --model large"
                    )
            # If Telugu found but wrong script also present
            elif (devanagari_count > telugu_count) or (tamil_count > telugu_count):
                wrong_script = 'Devanagari' if devanagari_count > tamil_count else 'Tamil'
                print(f"\n❌ ERROR: Telugu audio was transcribed in {wrong_script} script!")
                print(f"   Detected: {wrong_script.lower()}_count={devanagari_count if wrong_script == 'Devanagari' else tamil_count}, telugu_count={telugu_count}")
                raise TranscriptionError(
                    f"Telugu transcription failed: Output is mostly in {wrong_script} script, not Telugu. "
                    f"Model '{self.model_name}' is confusing scripts. "
                    f"Use --model large for Telugu. "
                    f"Command: python main.py {file_path.name} --language te --model large"
                )
            elif compression_ratio > 2.5:
                # Compression ratio > 2.5 indicates repetition
                print(f"\n❌ ERROR: High compression ratio ({compression_ratio:.2f}) indicates repetition!")
                print(f"   This is likely caused by small/medium models struggling with Telugu.")
                print(f"   SOLUTION: Use large model for Telugu")
                raise TranscriptionError(
                    f"Telugu transcription failed: Repetition detected (compression_ratio={compression_ratio:.2f}). "
                    f"Small/medium models cannot handle Telugu properly. "
                    f"Use --model large for Telugu. "
                    f"Command: python main.py {file_path.name} --language te --model large"
                )
            elif has_correct_script and compression_ratio <= 2.5:
                print(f"✅ Verified: Output contains Telugu script (compression_ratio: {compression_ratio:.2f})")
            else:
                print(f"⚠️  Warning: Telugu script validation inconclusive")
                print(f"   Telugu chars: {telugu_count}, Devanagari chars: {devanagari_count}, Tamil chars: {tamil_count}")
        
        # Validation for Hindi
        elif language == 'hi':
            devanagari_count = correct_script_count
            telugu_count = sum(1 for char in transcribed_text if 0x0C00 <= ord(char) <= 0x0C7F)
            tamil_count = sum(1 for char in transcribed_text if 0x0B80 <= ord(char) <= 0x0BFF)
            
            if is_mostly_roman and not has_correct_script:
                print(f"\n❌ ERROR: Hindi audio was transcribed in Roman script (English letters) instead of Devanagari!")
                print(f"   Detected: {roman_count} Roman characters, {devanagari_count} Devanagari characters")
                raise TranscriptionError(
                    f"Hindi transcription failed: Output is in Roman script, not Devanagari. "
                    f"Use --model medium for Hindi. "
                    f"Command: python main.py {file_path.name} --language hi --model medium"
                )
            elif (telugu_count > devanagari_count) or (tamil_count > devanagari_count):
                wrong_script = 'Telugu' if telugu_count > tamil_count else 'Tamil'
                print(f"\n❌ ERROR: Hindi audio was transcribed in {wrong_script} script!")
                raise TranscriptionError(
                    f"Hindi transcription failed: Output is in {wrong_script} script. "
                    f"Use --model medium for Hindi. "
                    f"Command: python main.py {file_path.name} --language hi --model medium"
                )
            elif compression_ratio > 3.0:
                # Stricter threshold for Hindi - medium model should handle this well
                print(f"\n❌ ERROR: High compression ratio ({compression_ratio:.2f}) indicates repetition!")
                raise TranscriptionError(
                    f"Hindi transcription failed: Repetition detected (compression_ratio={compression_ratio:.2f}). "
                    f"Use --model medium for Hindi to ensure strong transcription. "
                    f"Command: python main.py {file_path.name} --language hi --model medium"
                )
            elif has_correct_script and compression_ratio <= 2.5:
                print(f"✅ Verified: Output contains Devanagari script (compression_ratio: {compression_ratio:.2f})")
        
        # Validation for other Indian languages
        elif language in script_ranges:
            if is_mostly_roman and not has_correct_script:
                print(f"\n❌ ERROR: {script_name} audio was transcribed in Roman script instead of {script_name} script!")
                raise TranscriptionError(
                    f"{script_name} transcription failed: Output is in Roman script. "
                    f"Use --model medium for {script_name}. "
                    f"Command: python main.py {file_path.name} --language {language} --model medium"
                )
            elif compression_ratio > 3.0:
                # Stricter threshold - medium model should handle this well
                print(f"\n❌ ERROR: High compression ratio ({compression_ratio:.2f}) indicates repetition!")
                raise TranscriptionError(
                    f"{script_name} transcription failed: Repetition detected (compression_ratio={compression_ratio:.2f}). "
                    f"Use --model medium for {script_name} to ensure strong transcription. "
                    f"Command: python main.py {file_path.name} --language {language} --model medium"
                )
            elif has_correct_script and compression_ratio <= 2.5:
                print(f"✅ Verified: Output contains {script_name} script (compression_ratio: {compression_ratio:.2f})")
    
    def transcribe_with_paragraphs(
        self,
        file_path: Path,
        words_per_paragraph: Optional[int] = None,
        language: Optional[str] = None,
        temperature: Optional[float] = None
    ) -> Dict:
        """
        Transcribe and format into paragraphs
        
        Args:
            file_path: Path to audio/video file
            words_per_paragraph: Target words per paragraph (default from config)
            language: Language code. Auto-detect if None
            
        Returns:
            Dictionary with transcription and paragraphs
        """
        words_per_paragraph = words_per_paragraph or Config.PARAGRAPH_WORD_COUNT
        
        # Get transcription
        result = self.transcribe_file(file_path, language=language, temperature=temperature)
        
        # Format into paragraphs
        paragraphs = self._format_paragraphs(
            result['segments'],
            words_per_paragraph
        )
        
        return {
            'text': result['text'],
            'language': result['language'],
            'paragraphs': paragraphs,
            'segments': result['segments'],
            'full_result': result['full_result']
        }
    
    def _format_paragraphs(
        self,
        segments: List[Dict],
        words_per_paragraph: int
    ) -> List[Dict]:
        """
        Format segments into paragraphs based on word count
        
        Args:
            segments: List of transcription segments from Whisper
            words_per_paragraph: Target words per paragraph
            
        Returns:
            List of paragraph dictionaries with text, start, end times
        """
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
            
            # Initialize paragraph start time
            if current_paragraph['start'] is None:
                current_paragraph['start'] = segment_start
            
            # Add words to current paragraph
            for word in words:
                current_paragraph['words'].append(word)
                word_count += 1
                
                # Check if we've reached the target word count
                if word_count >= words_per_paragraph:
                    # Finalize current paragraph
                    current_paragraph['text'] = ' '.join(current_paragraph['words'])
                    current_paragraph['end'] = segment_end
                    paragraphs.append(current_paragraph)
                    
                    # Start new paragraph
                    current_paragraph = {
                        'text': '',
                        'words': [],
                        'start': None,
                        'end': None
                    }
                    word_count = 0
            
            # Update paragraph end time
            current_paragraph['end'] = segment_end
        
        # Add remaining words as final paragraph
        if current_paragraph['words']:
            current_paragraph['text'] = ' '.join(current_paragraph['words'])
            paragraphs.append(current_paragraph)
        
        return paragraphs
