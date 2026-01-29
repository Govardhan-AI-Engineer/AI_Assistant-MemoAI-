"""
URL handler for online media sources (YouTube, podcasts, etc.)
Task 2: Online Media Transcription
"""
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse
import yt_dlp
import requests
from src.core.exceptions import TranscriptionError
from src.core.config import Config


class URLHandler:
    """Handle URLs for online media sources"""
    
    # Supported URL patterns
    YOUTUBE_PATTERNS = [
        r'(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/)([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        r'(?:https?://)?(?:www\.)?youtube\.com/playlist\?list=([a-zA-Z0-9_-]+)',
    ]
    
    PODCAST_PATTERNS = [
        r'https?://.*\.(mp3|m4a|aac|wav|ogg|flac)',
        r'https?://.*\.(rss|xml)',  # RSS feeds
    ]
    
    @classmethod
    def is_url(cls, input_str: str) -> bool:
        """Check if input string is a URL"""
        try:
            result = urlparse(input_str)
            return all([result.scheme, result.netloc])
        except Exception:
            return False
    
    @classmethod
    def is_youtube_url(cls, url: str) -> bool:
        """Check if URL is a YouTube URL"""
        for pattern in cls.YOUTUBE_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def is_podcast_url(cls, url: str) -> bool:
        """Check if URL is a podcast/media URL"""
        # Check for direct media file URLs
        for pattern in cls.PODCAST_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    @classmethod
    def validate_url(cls, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL and determine type
        
        Returns:
            Tuple of (is_valid, url_type) where url_type is 'youtube', 'podcast', or None
        """
        if not cls.is_url(url):
            return False, None
        
        if cls.is_youtube_url(url):
            return True, 'youtube'
        elif cls.is_podcast_url(url):
            return True, 'podcast'
        else:
            # Try to fetch and check content type
            try:
                response = requests.head(url, timeout=10, allow_redirects=True)
                content_type = response.headers.get('Content-Type', '').lower()
                if any(media_type in content_type for media_type in ['audio', 'video']):
                    return True, 'podcast'
            except Exception:
                pass
            
            return True, 'unknown'
    
    @classmethod
    def download_youtube(cls, url: str, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Download audio from YouTube URL using yt-dlp
        
        Args:
            url: YouTube URL
            output_dir: Optional output directory (default: temp directory)
            
        Returns:
            Dictionary with 'audio_path' and 'metadata' (title, duration, etc.)
        """
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure yt-dlp options for reliable audio extraction
        # Enhanced configuration to avoid 403 errors and work with all YouTube videos
        ydl_opts = {
            # Format selection: prefer audio-only formats, fallback to video+audio
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio/best[height<=720]/best',
            'outtmpl': str(output_dir / '%(id)s.%(ext)s'),  # Use video ID for filename (more reliable)
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'quiet': False,
            'no_warnings': False,
            'noplaylist': True,  # Don't download playlists
            'extract_flat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            # Enhanced options to avoid 403 errors
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web'],  # Try android first, then web
                    'player_skip': ['webpage', 'configs'],  # Skip some checks that cause 403
                }
            },
            # Retry configuration
            'retries': 3,
            'fragment_retries': 3,
            # Additional headers to mimic browser
            'http_headers': {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive',
            },
        }
        
        try:
            # Try multiple strategies to avoid 403 errors
            strategies = [
                # Strategy 1: Android client (most reliable)
                {
                    **ydl_opts,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['android'],
                        }
                    }
                },
                # Strategy 2: Web client
                {
                    **ydl_opts,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['web'],
                        }
                    }
                },
                # Strategy 3: iOS client
                {
                    **ydl_opts,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['ios'],
                        }
                    }
                },
                # Strategy 4: Default (fallback)
                ydl_opts
            ]
            
            last_error = None
            info = None
            video_id = 'unknown'
            
            for i, strategy_opts in enumerate(strategies, 1):
                try:
                    with yt_dlp.YoutubeDL(strategy_opts) as ydl:
                        # Extract info first (without download) to get video ID and metadata
                        info = ydl.extract_info(url, download=False)
                        video_id = info.get('id', 'unknown')
                        
                        # Now download
                        ydl.download([url])
                        break  # Success, exit loop
                except yt_dlp.utils.DownloadError as e:
                    last_error = e
                    if i < len(strategies):
                        print(f"Strategy {i} failed, trying next strategy...")
                        continue
                    else:
                        raise  # All strategies failed
                except Exception as e:
                    last_error = e
                    if i < len(strategies):
                        print(f"Strategy {i} failed, trying next strategy...")
                        continue
                    else:
                        raise  # All strategies failed
            
            # If we get here, download succeeded - find the file
            if info is None:
                # Fallback: extract info one more time if we don't have it
                with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    video_id = info.get('id', 'unknown')
                
            # Find the downloaded file - look for WAV first (post-processed)
            audio_path = None
            
            # First, look for WAV file (post-processed)
            wav_files = list(output_dir.glob('*.wav'))
            if wav_files:
                audio_path = wav_files[0]
            else:
                # If no WAV, look for original format
                for ext in ['.m4a', '.webm', '.mp3', '.opus', '.ogg']:
                    files = list(output_dir.glob(f'*{ext}'))
                    if files:
                        audio_path = files[0]
                        break
            
            # If still not found, get any file in the directory
            if audio_path is None:
                all_files = list(output_dir.glob('*'))
                # Filter out any non-audio files
                audio_files = [f for f in all_files if f.suffix.lower() in ['.wav', '.m4a', '.mp3', '.webm', '.opus', '.ogg']]
                if audio_files:
                    audio_path = audio_files[0]
            
            if audio_path is None or not audio_path.exists():
                raise TranscriptionError("Failed to download YouTube audio - no valid audio file found")
            
            # Verify file is not empty
            if audio_path.stat().st_size == 0:
                raise TranscriptionError("Downloaded audio file is empty or corrupted")
            
            # If file is not WAV, we need to convert it
            if audio_path.suffix.lower() != '.wav':
                # Convert to WAV using FFmpeg
                wav_path = output_dir / f"{video_id}.wav"
                try:
                    cmd = [
                        'ffmpeg',
                        '-i', str(audio_path),
                        '-vn',  # No video
                        '-acodec', 'pcm_s16le',  # PCM 16-bit
                        '-ar', '16000',  # Sample rate 16kHz
                        '-ac', '1',  # Mono
                        '-y',  # Overwrite
                        str(wav_path)
                    ]
                    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                    if result.returncode == 0 and wav_path.exists():
                        # Remove original file
                        try:
                            audio_path.unlink()
                        except:
                            pass
                        audio_path = wav_path
                except Exception as e:
                    # If conversion fails, try to use original file
                    print(f"Warning: Could not convert to WAV, using original format: {e}")
            
            # Get title from info (already extracted during download)
            title = info.get('title', 'youtube_video') if info else 'youtube_video'
            
            return {
                'audio_path': audio_path,
                'metadata': {
                    'title': title,
                    'duration': info.get('duration', 0),
                    'uploader': info.get('uploader', 'Unknown'),
                    'url': url,
                    'source': 'youtube',
                    'video_id': video_id
                }
            }
                
        except yt_dlp.utils.DownloadError as e:
            error_msg = str(e)
            if '403' in error_msg or 'Forbidden' in error_msg:
                raise TranscriptionError(
                    f"YouTube download failed: HTTP 403 Forbidden. "
                    f"This may be due to YouTube restrictions. "
                    f"Try updating yt-dlp: pip install --upgrade yt-dlp"
                )
            raise TranscriptionError(f"YouTube download failed: {error_msg}")
        except Exception as e:
            raise TranscriptionError(f"YouTube download error: {str(e)}")
    
    @classmethod
    def download_podcast(cls, url: str, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Download audio from podcast/media URL
        
        Args:
            url: Podcast/media URL
            output_dir: Optional output directory (default: temp directory)
            
        Returns:
            Dictionary with 'audio_path' and 'metadata'
        """
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp())
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Determine file extension from URL or Content-Type
            response = requests.head(url, timeout=10, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '').lower()
            
            # Map content types to extensions
            ext_map = {
                'audio/mpeg': '.mp3',
                'audio/mp4': '.m4a',
                'audio/aac': '.aac',
                'audio/wav': '.wav',
                'audio/ogg': '.ogg',
                'audio/flac': '.flac',
            }
            
            ext = '.mp3'  # default
            for ct, extension in ext_map.items():
                if ct in content_type:
                    ext = extension
                    break
            
            # Try to get filename from URL
            parsed_url = urlparse(url)
            filename = Path(parsed_url.path).stem or 'podcast_audio'
            filename = re.sub(r'[^\w\s-]', '', filename).strip()
            if not filename:
                filename = 'podcast_audio'
            
            output_path = output_dir / f"{filename}{ext}"
            
            # Download the file
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            if not output_path.exists():
                raise TranscriptionError("Failed to download podcast audio")
            
            return {
                'audio_path': output_path,
                'metadata': {
                    'title': filename,
                    'url': url,
                    'source': 'podcast',
                    'content_type': content_type
                }
            }
            
        except requests.RequestException as e:
            raise TranscriptionError(f"Podcast download failed: {str(e)}")
        except Exception as e:
            raise TranscriptionError(f"Podcast download error: {str(e)}")
    
    @classmethod
    def download_media(cls, url: str, output_dir: Optional[Path] = None) -> Dict[str, Path]:
        """
        Download media from URL (auto-detect type)
        
        Args:
            url: Media URL (YouTube, podcast, etc.)
            output_dir: Optional output directory
            
        Returns:
            Dictionary with 'audio_path' and 'metadata'
        """
        is_valid, url_type = cls.validate_url(url)
        
        if not is_valid:
            raise TranscriptionError(f"Invalid URL: {url}")
        
        if url_type == 'youtube':
            return cls.download_youtube(url, output_dir)
        elif url_type == 'podcast':
            return cls.download_podcast(url, output_dir)
        else:
            # Try as podcast (direct media file)
            try:
                return cls.download_podcast(url, output_dir)
            except Exception as e:
                raise TranscriptionError(
                    f"Unsupported URL type: {url}. "
                    f"Supported: YouTube URLs and direct audio/video file URLs. "
                    f"Error: {str(e)}"
                )
