"""
Audio validation module to detect corrupted or incomplete downloads
Especially important for YouTube Shorts and podcasts
"""
import subprocess
from pathlib import Path
from typing import Dict, Optional, Tuple
from src.core.exceptions import TranscriptionError


class AudioValidator:
    """Validate audio files for corruption, completeness, and quality"""
    
    MIN_FILE_SIZE = 1024  # 1KB minimum file size
    MIN_DURATION = 0.1  # 0.1 seconds minimum duration
    MAX_DURATION = 86400  # 24 hours maximum (sanity check)
    
    @classmethod
    def validate(
        cls,
        audio_path: Path,
        expected_duration: Optional[float] = None,
        source: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Validate audio file for corruption and completeness
        
        Args:
            audio_path: Path to audio file
            expected_duration: Expected duration in seconds (if known)
            source: Source type ('youtube', 'podcast', 'file', etc.)
            
        Returns:
            Tuple of (is_valid, validation_report)
        """
        report = {
            'is_valid': False,
            'errors': [],
            'warnings': [],
            'metadata': {},
            'source': source
        }
        
        # Check 1: File exists
        if not audio_path.exists():
            report['errors'].append("File does not exist")
            return False, report
        
        # Check 2: File size
        file_size = audio_path.stat().st_size
        if file_size < cls.MIN_FILE_SIZE:
            report['errors'].append(
                f"File too small ({file_size} bytes < {cls.MIN_FILE_SIZE} bytes). "
                f"File may be corrupted or incomplete."
            )
            return False, report
        
        report['metadata']['file_size'] = file_size
        
        # Check 3: FFprobe validation (check if file is valid audio)
        probe_result = cls._probe_audio(audio_path)
        if not probe_result['is_valid']:
            report['errors'].extend(probe_result['errors'])
            return False, report
        
        duration = probe_result.get('duration', 0)
        report['metadata'].update(probe_result.get('metadata', {}))
        
        # Check 4: Duration validation
        if duration < cls.MIN_DURATION:
            report['errors'].append(
                f"Audio duration too short ({duration:.2f}s < {cls.MIN_DURATION}s). "
                f"File may be corrupted."
            )
            return False, report
        
        if duration > cls.MAX_DURATION:
            report['warnings'].append(
                f"Audio duration very long ({duration:.2f}s). "
                f"This may be a processing error."
            )
        
        # Check 5: Expected duration check (for downloads)
        if expected_duration is not None and source in ['youtube', 'podcast']:
            duration_diff = abs(duration - expected_duration)
            duration_diff_percent = (duration_diff / expected_duration) * 100 if expected_duration > 0 else 0
            
            # Allow 5% tolerance for duration mismatch
            if duration_diff_percent > 5:
                report['warnings'].append(
                    f"Duration mismatch: expected {expected_duration:.2f}s, "
                    f"got {duration:.2f}s (diff: {duration_diff_percent:.1f}%). "
                    f"Download may be incomplete."
                )
                
                # If difference is > 20%, consider it an error
                if duration_diff_percent > 20:
                    report['errors'].append(
                        f"Significant duration mismatch ({duration_diff_percent:.1f}%). "
                        f"Download likely incomplete or corrupted."
                    )
                    return False, report
        
        # Check 6: Audio stream validation
        if not probe_result.get('has_audio_stream', False):
            report['errors'].append("No audio stream found in file")
            return False, report
        
        # Check 7: Silent audio detection (for corrupted downloads)
        if cls._is_likely_silent(audio_path, duration):
            report['warnings'].append(
                "Audio appears to be silent or very quiet. "
                "This may indicate a corrupted download."
            )
        
        # All checks passed
        report['is_valid'] = True
        report['metadata']['duration'] = duration
        
        return True, report
    
    @classmethod
    def _probe_audio(cls, audio_path: Path) -> Dict:
        """Probe audio file using FFprobe"""
        result = {
            'is_valid': False,
            'errors': [],
            'metadata': {},
            'has_audio_stream': False,
            'duration': 0
        }
        
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(audio_path)
            ]
            
            probe_result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            if probe_result.returncode != 0:
                result['errors'].append(
                    f"FFprobe failed: {probe_result.stderr[:200]}"
                )
                return result
            
            try:
                import json
                probe_data = json.loads(probe_result.stdout)
            except (ImportError, json.JSONDecodeError) as e:
                result['errors'].append(f"Failed to parse FFprobe output: {str(e)}")
                return result
            
            # Check for audio streams
            audio_streams = [
                s for s in probe_data.get('streams', [])
                if s.get('codec_type') == 'audio'
            ]
            
            if not audio_streams:
                result['errors'].append("No audio streams found in file")
                return result
            
            result['has_audio_stream'] = True
            
            # Get format info
            format_info = probe_data.get('format', {})
            duration = float(format_info.get('duration', 0))
            
            if duration <= 0:
                # Try to get duration from stream
                for stream in audio_streams:
                    if 'duration' in stream:
                        try:
                            duration = float(stream['duration'])
                            if duration > 0:
                                break
                        except (ValueError, TypeError):
                            pass
            
            result['duration'] = duration
            result['metadata'] = {
                'format': format_info.get('format_name', 'unknown'),
                'size': int(format_info.get('size', 0)),
                'bitrate': int(format_info.get('bit_rate', 0)),
                'codec': audio_streams[0].get('codec_name', 'unknown') if audio_streams else 'unknown',
                'sample_rate': int(audio_streams[0].get('sample_rate', 0)) if audio_streams else 0,
                'channels': int(audio_streams[0].get('channels', 0)) if audio_streams else 0
            }
            
            result['is_valid'] = True
            
        except FileNotFoundError:
            result['errors'].append(
                "FFprobe not found. Please install FFmpeg: "
                "https://ffmpeg.org/download.html"
            )
        except json.JSONDecodeError:
            result['errors'].append("Failed to parse FFprobe output")
        except Exception as e:
            result['errors'].append(f"Audio probe error: {str(e)}")
        
        return result
    
    @classmethod
    def _is_likely_silent(cls, audio_path: Path, duration: float) -> bool:
        """
        Check if audio is likely silent (corrupted download indicator)
        Uses FFmpeg to analyze audio levels
        """
        if duration < 1.0:  # Too short to analyze
            return False
        
        try:
            # Use FFmpeg to detect silence
            # This checks if audio has very low volume (likely silent/corrupted)
            cmd = [
                'ffmpeg',
                '-i', str(audio_path),
                '-af', 'silencedetect=noise=-50dB:d=0.5',
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Count silence detections
            silence_count = result.stderr.count('silence_start')
            
            # If more than 80% of the audio is detected as silence, it's likely corrupted
            silence_ratio = silence_count / max(1, int(duration))
            
            return silence_ratio > 0.8
            
        except Exception:
            # If silence detection fails, assume not silent
            return False
    
    @classmethod
    def validate_download_completeness(
        cls,
        audio_path: Path,
        expected_metadata: Dict,
        source: str = 'youtube'
    ) -> Tuple[bool, Dict]:
        """
        Validate that a downloaded audio file is complete
        
        Args:
            audio_path: Path to downloaded audio file
            expected_metadata: Expected metadata (duration, size, etc.)
            source: Source type ('youtube', 'podcast', etc.)
            
        Returns:
            Tuple of (is_complete, validation_report)
        """
        expected_duration = expected_metadata.get('duration')
        
        is_valid, report = cls.validate(
            audio_path,
            expected_duration=expected_duration,
            source=source
        )
        
        if not is_valid:
            return False, report
        
        # Additional checks for download completeness
        actual_duration = report['metadata'].get('duration', 0)
        
        # For YouTube Shorts, check if duration matches expected
        if source == 'youtube' and expected_duration:
            duration_diff = abs(actual_duration - expected_duration)
            if duration_diff > 2.0:  # More than 2 seconds difference
                report['warnings'].append(
                    f"Download may be incomplete: "
                    f"expected {expected_duration:.2f}s, got {actual_duration:.2f}s"
                )
        
        # Check file size reasonableness
        file_size = report['metadata'].get('file_size', 0)
        if actual_duration > 0:
            # Estimate expected size (rough: ~16KB per second for 16kHz mono 16-bit)
            estimated_size = actual_duration * 16000 * 2  # 16kHz * 2 bytes per sample
            if file_size < estimated_size * 0.5:  # Less than 50% of expected
                report['warnings'].append(
                    f"File size seems too small for duration. "
                    f"May indicate incomplete download."
                )
        
        return is_valid, report
