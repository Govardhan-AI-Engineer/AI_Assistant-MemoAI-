"""
Subtitle file parser for SRT and VTT formats
Task 2: Online Media Transcription
"""
from pathlib import Path
from typing import Dict, List, Optional
import pysrt
import webvtt
from src.core.exceptions import TranscriptionError


class SubtitleParser:
    """Parse SRT and VTT subtitle files"""
    
    @classmethod
    def is_subtitle_file(cls, file_path: Path) -> bool:
        """Check if file is a subtitle file"""
        return file_path.suffix.lower() in ['.srt', '.vtt']
    
    @classmethod
    def parse_srt(cls, file_path: Path) -> Dict:
        """
        Parse SRT subtitle file
        
        Args:
            file_path: Path to SRT file
            
        Returns:
            Dictionary with transcription data
        """
        if not file_path.exists():
            raise TranscriptionError(f"SRT file not found: {file_path}")
        
        try:
            subtitles = pysrt.open(str(file_path), encoding='utf-8')
            
            # Extract text and segments
            segments = []
            full_text = []
            
            for sub in subtitles:
                segment_text = sub.text.strip()
                if segment_text:
                    segments.append({
                        'start': sub.start.ordinal / 1000.0,  # Convert to seconds
                        'end': sub.end.ordinal / 1000.0,
                        'text': segment_text
                    })
                    full_text.append(segment_text)
            
            return {
                'text': ' '.join(full_text),
                'segments': segments,
                'language': None,  # SRT doesn't contain language info
                'full_result': {
                    'segments': segments
                },
                'metadata': {
                    'source_file': str(file_path),
                    'format': 'srt',
                    'segment_count': len(segments)
                }
            }
            
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                subtitles = pysrt.open(str(file_path), encoding='latin-1')
                segments = []
                full_text = []
                
                for sub in subtitles:
                    segment_text = sub.text.strip()
                    if segment_text:
                        segments.append({
                            'start': sub.start.ordinal / 1000.0,
                            'end': sub.end.ordinal / 1000.0,
                            'text': segment_text
                        })
                        full_text.append(segment_text)
                
                return {
                    'text': ' '.join(full_text),
                    'segments': segments,
                    'language': None,
                    'full_result': {
                        'segments': segments
                    },
                    'metadata': {
                        'source_file': str(file_path),
                        'format': 'srt',
                        'segment_count': len(segments)
                    }
                }
            except Exception as e:
                raise TranscriptionError(f"Failed to parse SRT file: {str(e)}")
        except Exception as e:
            raise TranscriptionError(f"Failed to parse SRT file: {str(e)}")
    
    @classmethod
    def parse_vtt(cls, file_path: Path) -> Dict:
        """
        Parse VTT subtitle file
        
        Args:
            file_path: Path to VTT file
            
        Returns:
            Dictionary with transcription data
        """
        if not file_path.exists():
            raise TranscriptionError(f"VTT file not found: {file_path}")
        
        try:
            captions = webvtt.read(str(file_path))
            
            segments = []
            full_text = []
            
            for caption in captions:
                text = caption.text.strip()
                if text:
                    # Convert timestamp to seconds
                    start_seconds = cls._vtt_time_to_seconds(caption.start)
                    end_seconds = cls._vtt_time_to_seconds(caption.end)
                    
                    segments.append({
                        'start': start_seconds,
                        'end': end_seconds,
                        'text': text
                    })
                    full_text.append(text)
            
            return {
                'text': ' '.join(full_text),
                'segments': segments,
                'language': None,  # VTT doesn't contain language info
                'full_result': {
                    'segments': segments
                },
                'metadata': {
                    'source_file': str(file_path),
                    'format': 'vtt',
                    'segment_count': len(segments)
                }
            }
            
        except Exception as e:
            raise TranscriptionError(f"Failed to parse VTT file: {str(e)}")
    
    @classmethod
    def _vtt_time_to_seconds(cls, time_str: str) -> float:
        """Convert VTT timestamp to seconds"""
        try:
            # VTT format: HH:MM:SS.mmm
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds_parts = parts[2].split('.')
                seconds = int(seconds_parts[0])
                milliseconds = int(seconds_parts[1]) if len(seconds_parts) > 1 else 0
                return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
            return 0.0
        except Exception:
            return 0.0
    
    @classmethod
    def parse_subtitle(cls, file_path: Path) -> Dict:
        """
        Parse subtitle file (auto-detect format)
        
        Args:
            file_path: Path to subtitle file (SRT or VTT)
            
        Returns:
            Dictionary with transcription data
        """
        if not cls.is_subtitle_file(file_path):
            raise TranscriptionError(
                f"Not a subtitle file: {file_path}. "
                f"Supported formats: .srt, .vtt"
            )
        
        ext = file_path.suffix.lower()
        
        if ext == '.srt':
            return cls.parse_srt(file_path)
        elif ext == '.vtt':
            return cls.parse_vtt(file_path)
        else:
            raise TranscriptionError(f"Unsupported subtitle format: {ext}")
