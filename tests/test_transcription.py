"""
Tests for transcription module (Task 1)
"""
import pytest
from pathlib import Path
from src.transcription import TranscriptionService, AudioExtractor
from src.core.exceptions import TranscriptionError


class TestAudioExtractor:
    """Tests for audio extraction"""
    
    def test_is_video_file(self):
        """Test video file detection"""
        assert AudioExtractor.is_video_file(Path("test.mp4")) is True
        assert AudioExtractor.is_video_file(Path("test.avi")) is True
        assert AudioExtractor.is_video_file(Path("test.mp3")) is False
    
    def test_is_audio_file(self):
        """Test audio file detection"""
        assert AudioExtractor.is_audio_file(Path("test.mp3")) is True
        assert AudioExtractor.is_audio_file(Path("test.aac")) is True
        assert AudioExtractor.is_audio_file(Path("test.mp4")) is False
    
    def test_is_supported_format(self):
        """Test supported format detection"""
        assert AudioExtractor.is_supported_format(Path("test.mp4")) is True
        assert AudioExtractor.is_supported_format(Path("test.mp3")) is True
        assert AudioExtractor.is_supported_format(Path("test.xyz")) is False


class TestTranscriptionService:
    """Tests for transcription service"""
    
    def test_get_supported_formats(self):
        """Test getting supported formats"""
        service = TranscriptionService()
        formats = service.get_supported_formats()
        
        assert 'video' in formats
        assert 'audio' in formats
        assert '.mp4' in formats['video']
        assert '.mp3' in formats['audio']
    
    def test_transcribe_nonexistent_file(self):
        """Test transcription with non-existent file"""
        service = TranscriptionService()
        
        with pytest.raises(TranscriptionError):
            service.transcribe(Path("nonexistent.mp3"))


# Note: Full integration tests require actual audio/video files
# These can be added when test files are available
