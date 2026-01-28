"""
Custom exceptions for MemoAI
"""


class MemoAIException(Exception):
    """Base exception for MemoAI"""
    pass


class TranscriptionError(MemoAIException):
    """Transcription related errors"""
    pass


class TranslationError(MemoAIException):
    """Translation related errors"""
    pass


class ExportError(MemoAIException):
    """Export related errors"""
    pass


class MemoryError(MemoAIException):
    """Memory/storage related errors"""
    pass
