"""
Audio extraction utilities for video files
"""
import subprocess
import tempfile
import re
import sys
from pathlib import Path
from typing import Optional
from src.core.exceptions import TranscriptionError


class AudioExtractor:
    """Extract audio from video files using FFmpeg"""
    
    SUPPORTED_VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv'}
    SUPPORTED_AUDIO_FORMATS = {'.mp3', '.aac', '.m4a', '.wav', '.flac', '.ogg'}
    
    @classmethod
    def is_video_file(cls, file_path: Path) -> bool:
        """Check if file is a video format"""
        return file_path.suffix.lower() in cls.SUPPORTED_VIDEO_FORMATS
    
    @classmethod
    def is_audio_file(cls, file_path: Path) -> bool:
        """Check if file is an audio format"""
        return file_path.suffix.lower() in cls.SUPPORTED_AUDIO_FORMATS
    
    @classmethod
    def is_supported_format(cls, file_path: Path) -> bool:
        """Check if file format is supported"""
        return cls.is_video_file(file_path) or cls.is_audio_file(file_path)
    
    @classmethod
    def extract_audio(cls, input_path: Path, output_path: Optional[Path] = None) -> Path:
        """
        Extract audio from video file to WAV format
        
        Args:
            input_path: Path to input video/audio file
            output_path: Optional output path. If None, creates temp file
            
        Returns:
            Path to extracted audio file
        """
        if not input_path.exists():
            raise TranscriptionError(f"Input file not found: {input_path}")
        
        if not cls.is_supported_format(input_path):
            raise TranscriptionError(
                f"Unsupported file format: {input_path.suffix}. "
                f"Supported: {cls.SUPPORTED_VIDEO_FORMATS | cls.SUPPORTED_AUDIO_FORMATS}"
            )
        
        # If it's already an audio file, return as-is (or convert to WAV)
        if cls.is_audio_file(input_path):
            if output_path is None:
                # Create temp file for conversion
                output_path = Path(tempfile.mktemp(suffix='.wav'))
            else:
                output_path = output_path.with_suffix('.wav')
        else:
            # Video file - extract audio
            if output_path is None:
                output_path = Path(tempfile.mktemp(suffix='.wav'))
        
        try:
            # Use FFmpeg to extract/convert audio to WAV
            # Optimized with threading for faster processing (no quality loss)
            cmd = [
                'ffmpeg',
                '-threads', '0',  # Use all CPU cores for faster processing
                '-i', str(input_path),
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit
                '-ar', '16000',  # Sample rate 16kHz (Whisper works well with this)
                '-ac', '1',  # Mono
                '-y',  # Overwrite output
                str(output_path)
            ]
            
            # Get video duration first for progress calculation
            duration = None
            try:
                probe_cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'format=duration',
                    '-of', 'default=noprint_wrappers=1:nokey=1',
                    str(input_path)
                ]
                probe_result = subprocess.run(
                    probe_cmd,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=10
                )
                if probe_result.returncode == 0 and probe_result.stdout.strip():
                    duration = float(probe_result.stdout.strip())
            except (ValueError, subprocess.TimeoutExpired, FileNotFoundError):
                pass  # Duration detection failed, progress will be time-based only
            
            # Run FFmpeg with real-time progress output
            print(f"📹 Extracting audio from video: {input_path.name}")
            process = subprocess.Popen(
                cmd,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Parse FFmpeg progress output (goes to stderr)
            stderr_output = []
            progress_pattern = re.compile(r'time=(\d+):(\d+):(\d+\.\d+)')
            last_progress = 0
            
            # Read stderr line by line to get progress updates
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    stderr_output.append(output)
                    # Parse time from output (format: time=HH:MM:SS.ms)
                    match = progress_pattern.search(output)
                    if match:
                        try:
                            hours, minutes, seconds = map(float, match.groups())
                            current_time = hours * 3600 + minutes * 60 + seconds
                            
                            if duration and duration > 0:
                                progress_percent = min(100, (current_time / duration) * 100)
                                # Only update if progress changed significantly (avoid spam)
                                if abs(progress_percent - last_progress) >= 1.0 or progress_percent >= 100:
                                    print(f"   ⏳ Extraction progress: {progress_percent:.1f}% ({int(current_time)}s / {int(duration)}s)", end='\r')
                                    sys.stdout.flush()
                                    last_progress = progress_percent
                            else:
                                # If duration unknown, just show elapsed time
                                print(f"   ⏳ Extracting... ({int(current_time)}s elapsed)", end='\r')
                                sys.stdout.flush()
                        except (ValueError, TypeError):
                            pass  # Skip invalid time values
            
            # Wait for process to complete and get return code
            returncode = process.wait()
            stderr_text = ''.join(stderr_output)
            
            if returncode != 0:
                raise TranscriptionError(
                    f"FFmpeg extraction failed: {stderr_text}"
                )
            
            # Print completion
            if duration:
                print(f"\n   ✅ Extraction complete: 100.0% ({int(duration)}s)")
            else:
                print(f"\n   ✅ Extraction complete")
            
            if not output_path.exists():
                raise TranscriptionError("Audio extraction failed: output file not created")
            
            return output_path
            
        except FileNotFoundError:
            raise TranscriptionError(
                "FFmpeg not found. Please install FFmpeg: "
                "https://ffmpeg.org/download.html"
            )
        except Exception as e:
            raise TranscriptionError(f"Audio extraction error: {str(e)}")
