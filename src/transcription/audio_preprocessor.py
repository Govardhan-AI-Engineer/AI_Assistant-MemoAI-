"""
Advanced audio preprocessing module for robust transcription
Handles noise reduction, normalization, channel fixing, and resampling
"""
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
from src.core.exceptions import TranscriptionError


class AudioPreprocessor:
    """Advanced audio preprocessing using FFmpeg for optimal transcription quality"""
    
    # Optimal audio parameters for Whisper
    TARGET_SAMPLE_RATE = 16000  # Whisper's native sample rate
    TARGET_CHANNELS = 1  # Mono
    TARGET_BIT_DEPTH = 16  # 16-bit PCM
    
    @classmethod
    def preprocess(
        cls,
        input_path: Path,
        output_path: Optional[Path] = None,
        enable_noise_reduction: bool = True,
        enable_normalization: bool = True,
        enable_channel_fix: bool = True,
        noise_reduction_strength: float = 0.5
    ) -> Tuple[Path, Dict]:
        """
        Preprocess audio file for optimal transcription quality
        
        Args:
            input_path: Path to input audio/video file
            output_path: Optional output path. If None, creates temp file
            enable_noise_reduction: Enable noise reduction filter
            enable_normalization: Enable audio normalization
            enable_channel_fix: Fix stereo/mono channel issues
            noise_reduction_strength: Noise reduction strength (0.0-1.0)
            
        Returns:
            Tuple of (output_path, metadata_dict)
        """
        if not input_path.exists():
            raise TranscriptionError(f"Input file not found: {input_path}")
        
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix='.wav'))
        else:
            output_path = output_path.with_suffix('.wav')
        
        try:
            # Build FFmpeg filter chain
            filters = []
            
            # Step 1: Channel handling (convert to mono, fix channel issues)
            if enable_channel_fix:
                filters.append("pan=mono|c0=0.5*c0+0.5*c1")  # Mix stereo to mono
            
            # Step 2: Noise reduction (using highpass and lowpass filters + denoise)
            if enable_noise_reduction:
                # Highpass filter to remove low-frequency noise (below 80Hz)
                filters.append(f"highpass=f=80")
                # Lowpass filter to remove high-frequency noise (above 12000Hz for 16kHz sample rate)
                filters.append(f"lowpass=f=12000")
                # Denoise filter (afftdn - adaptive FFT denoiser)
                # strength: 0.0-1.0, higher = more aggressive
                filters.append(f"afftdn=nr={noise_reduction_strength}")
            
            # Step 3: Normalization (loudnorm for consistent volume)
            if enable_normalization:
                # Use loudnorm for broadcast-standard normalization
                # This ensures consistent volume levels across different audio sources
                filters.append("loudnorm=I=-16:TP=-1.5:LRA=11")
            
            # Step 4: Resampling and format conversion
            filter_chain = ",".join(filters) if filters else None
            
            # Build FFmpeg command
            # Optimized with threading for faster processing (no quality loss)
            cmd = [
                'ffmpeg',
                '-threads', '0',  # Use all CPU cores for faster processing
                '-i', str(input_path),
                '-vn',  # No video
            ]
            
            # Add filter chain if we have filters
            if filter_chain:
                cmd.extend(['-af', filter_chain])
            
            # Output format settings
            cmd.extend([
                '-acodec', 'pcm_s16le',  # PCM 16-bit little-endian
                '-ar', str(cls.TARGET_SAMPLE_RATE),  # Sample rate
                '-ac', str(cls.TARGET_CHANNELS),  # Channels (mono)
                '-y',  # Overwrite output
                str(output_path)
            ])
            
            # Execute FFmpeg
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                # If preprocessing fails, try simpler conversion without filters
                print(f"⚠️  Advanced preprocessing failed, trying basic conversion: {result.stderr[:200]}")
                return cls._basic_preprocess(input_path, output_path)
            
            if not output_path.exists():
                raise TranscriptionError("Audio preprocessing failed: output file not created")
            
            # Get audio metadata
            metadata = cls._get_audio_metadata(output_path)
            
            return output_path, metadata
            
        except FileNotFoundError:
            raise TranscriptionError(
                "FFmpeg not found. Please install FFmpeg: "
                "https://ffmpeg.org/download.html"
            )
        except Exception as e:
            raise TranscriptionError(f"Audio preprocessing error: {str(e)}")
    
    @classmethod
    def _basic_preprocess(cls, input_path: Path, output_path: Path) -> Tuple[Path, Dict]:
        """Fallback: Basic audio conversion without advanced filters"""
        # Optimized with threading for faster processing (no quality loss)
        cmd = [
            'ffmpeg',
            '-threads', '0',  # Use all CPU cores for faster processing
            '-i', str(input_path),
            '-vn',
            '-acodec', 'pcm_s16le',
            '-ar', str(cls.TARGET_SAMPLE_RATE),
            '-ac', str(cls.TARGET_CHANNELS),
            '-y',
            str(output_path)
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            raise TranscriptionError(f"Basic audio conversion failed: {result.stderr}")
        
        if not output_path.exists():
            raise TranscriptionError("Audio conversion failed: output file not created")
        
        metadata = cls._get_audio_metadata(output_path)
        return output_path, metadata
    
    @classmethod
    def _get_audio_metadata(cls, audio_path: Path) -> Dict:
        """Get audio file metadata using FFprobe"""
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(audio_path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode == 0:
                try:
                    import json
                    probe_data = json.loads(result.stdout)
                except ImportError:
                    # Fallback if json not available (shouldn't happen in Python 3+)
                    return cls._get_fallback_metadata(audio_path)
                
                # Extract audio stream info
                audio_stream = None
                for stream in probe_data.get('streams', []):
                    if stream.get('codec_type') == 'audio':
                        audio_stream = stream
                        break
                
                format_info = probe_data.get('format', {})
                
                duration = float(format_info.get('duration', 0))
                size = int(format_info.get('size', 0))
                bitrate = int(format_info.get('bit_rate', 0))
                
                sample_rate = int(audio_stream.get('sample_rate', cls.TARGET_SAMPLE_RATE)) if audio_stream else cls.TARGET_SAMPLE_RATE
                channels = int(audio_stream.get('channels', cls.TARGET_CHANNELS)) if audio_stream else cls.TARGET_CHANNELS
                
                return {
                    'duration': duration,
                    'size_bytes': size,
                    'bitrate': bitrate,
                    'sample_rate': sample_rate,
                    'channels': channels,
                    'format': format_info.get('format_name', 'unknown')
                }
        except Exception as e:
            print(f"Warning: Could not get audio metadata: {e}")
        
        # Fallback metadata
        return cls._get_fallback_metadata(audio_path)
    
    @classmethod
    def _get_fallback_metadata(cls, audio_path: Path) -> Dict:
        """Get fallback metadata when FFprobe fails"""
        return {
            'duration': 0,
            'size_bytes': audio_path.stat().st_size if audio_path.exists() else 0,
            'bitrate': 0,
            'sample_rate': cls.TARGET_SAMPLE_RATE,
            'channels': cls.TARGET_CHANNELS,
            'format': 'unknown'
        }
    
    @classmethod
    def detect_audio_quality(cls, audio_path: Path) -> Dict[str, any]:
        """
        Analyze audio quality metrics
        
        Returns:
            Dict with quality metrics:
            - duration: Audio duration in seconds
            - estimated_quality: 'high', 'medium', 'low'
            - has_noise: bool
            - is_stereo: bool
            - sample_rate: int
            - bitrate: int
        """
        metadata = cls._get_audio_metadata(audio_path)
        
        duration = metadata.get('duration', 0)
        sample_rate = metadata.get('sample_rate', 0)
        bitrate = metadata.get('bitrate', 0)
        channels = metadata.get('channels', 1)
        
        # Estimate quality based on bitrate and sample rate
        quality_score = 0
        
        # Sample rate scoring
        if sample_rate >= 44100:
            quality_score += 3
        elif sample_rate >= 22050:
            quality_score += 2
        elif sample_rate >= 16000:
            quality_score += 1
        
        # Bitrate scoring (for compressed formats)
        if bitrate > 0:
            if bitrate >= 192000:  # 192 kbps
                quality_score += 3
            elif bitrate >= 128000:  # 128 kbps
                quality_score += 2
            elif bitrate >= 64000:  # 64 kbps
                quality_score += 1
        
        # Determine quality level
        if quality_score >= 5:
            estimated_quality = 'high'
        elif quality_score >= 3:
            estimated_quality = 'medium'
        else:
            estimated_quality = 'low'
        
        return {
            'duration': duration,
            'estimated_quality': estimated_quality,
            'has_noise': estimated_quality == 'low',  # Heuristic: low quality likely has noise
            'is_stereo': channels > 1,
            'sample_rate': sample_rate,
            'bitrate': bitrate,
            'channels': channels,
            'quality_score': quality_score
        }
