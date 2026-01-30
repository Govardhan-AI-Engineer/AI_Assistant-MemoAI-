"""
Translation module - Multi-provider translation with fallback
"""
# Core imports (always available)
from src.translation.base_provider import TranslationGranularity, TranslationProvider
from src.translation.exceptions import (
    TranslationError,
    ProviderUnavailableError,
    TranslationTimeoutError,
    TranslationQualityError
)

# Service imports (may fail if dependencies missing, but we handle it)
try:
    from src.translation.service import TranslationService
except ImportError:
    TranslationService = None

try:
    from src.translation.orchestrator import TranslationOrchestrator
except ImportError:
    TranslationOrchestrator = None

# Provider imports (optional, may not be available if dependencies missing)
try:
    from src.translation.google_provider import GoogleTranslateProvider
except ImportError:
    GoogleTranslateProvider = None

try:
    from src.translation.libre_provider import LibreTranslateProvider
except ImportError:
    LibreTranslateProvider = None

try:
    from src.translation.deepl_provider import DeepLProvider
except ImportError:
    DeepLProvider = None

try:
    from src.translation.ai_provider import AITranslationProvider
except ImportError:
    AITranslationProvider = None

# Robust translation components (for code-mixed multilingual speech)
try:
    from src.translation.text_normalizer import TextNormalizer
except ImportError:
    TextNormalizer = None

try:
    from src.translation.robust_translator import RobustTranslator
except ImportError:
    RobustTranslator = None

try:
    from src.translation.robust_integration import RobustTranscriptionTranslationIntegration
except ImportError:
    RobustTranscriptionTranslationIntegration = None

try:
    from src.translation.llm_refiner import LLMRefiner
except ImportError:
    LLMRefiner = None

__all__ = [
    'TranslationService',
    'TranslationGranularity',
    'TranslationProvider',
    'TranslationOrchestrator',
    'GoogleTranslateProvider',
    'LibreTranslateProvider',
    'DeepLProvider',
    'AITranslationProvider',
    'TranslationError',
    'ProviderUnavailableError',
    'TranslationTimeoutError',
    'TranslationQualityError',
    # Robust translation components
    'TextNormalizer',
    'RobustTranslator',
    'RobustTranscriptionTranslationIntegration',
    'LLMRefiner'
]
