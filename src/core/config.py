"""
Configuration management for MemoAI
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Application configuration"""
    
    # Project paths
    BASE_DIR = Path(__file__).parent.parent.parent
    DATA_DIR = BASE_DIR / "data"
    TRANSCRIPTS_DIR = DATA_DIR / "transcripts"
    NOTES_DIR = DATA_DIR / "notes"
    EXPORTS_DIR = DATA_DIR / "exports"
    
    # Transcription settings (Whisper - Free & Open-Source)
    # Default to medium for better accuracy across all languages
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")  # tiny, base, small, medium, large
    PARAGRAPH_WORD_COUNT = int(os.getenv("PARAGRAPH_WORD_COUNT", "50"))
    WHISPER_TEMPERATURE = float(os.getenv("WHISPER_TEMPERATURE", "0"))  # 0 = deterministic, higher = more variation
    # For better accuracy with non-English languages, use larger models (small, medium, or large)
    # Indian languages (Telugu, Hindi, Tamil, etc.) work better with 'small' or larger models
    
    # Translation settings
    DEFAULT_TRANSLATION_SERVICE = os.getenv("DEFAULT_TRANSLATION_SERVICE", "google")
    TRANSLATION_SERVICES = ["google", "libre", "deepl", "ai"]  # Added "ai" to services
    TRANSLATION_PROVIDER_PRIORITY = os.getenv(
        "TRANSLATION_PROVIDER_PRIORITY",
        "google,libre,deepl,ai"  # AI added as fallback (will be preferred for Telugu automatically)
    ).split(",")
    ENABLE_RETRANSLATION = os.getenv("ENABLE_RETRANSLATION", "true").lower() == "true"
    
    # Translation API keys (from environment)
    # DEEPL_API_KEY - Set in environment
    # LIBRETRANSLATE_API_KEY - Set in environment (optional)
    # LIBRETRANSLATE_API_URL - Set in environment (optional, defaults to public API)
    # GROQ_API_KEY - Set in environment for AI Translation (get from https://console.groq.com)
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/memoai.db")
    
    # Create directories
    @classmethod
    def setup_directories(cls):
        """Create necessary directories"""
        cls.DATA_DIR.mkdir(exist_ok=True)
        cls.TRANSCRIPTS_DIR.mkdir(exist_ok=True)
        cls.NOTES_DIR.mkdir(exist_ok=True)
        cls.EXPORTS_DIR.mkdir(exist_ok=True)
        
        # Create export subdirectories
        (cls.EXPORTS_DIR / "subtitles").mkdir(exist_ok=True)
        (cls.EXPORTS_DIR / "documents").mkdir(exist_ok=True)
        (cls.EXPORTS_DIR / "audio").mkdir(exist_ok=True)

# Initialize directories
Config.setup_directories()
