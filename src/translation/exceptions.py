"""
Translation-specific exceptions
"""
from src.core.exceptions import TranscriptionError


class TranslationError(TranscriptionError):
    """Base exception for translation errors"""
    pass


class ProviderUnavailableError(TranslationError):
    """Raised when a translation provider is unavailable"""
    pass


class TranslationTimeoutError(TranslationError):
    """Raised when translation times out"""
    pass


class TranslationQualityError(TranslationError):
    """Raised when translation quality is poor"""
    pass
