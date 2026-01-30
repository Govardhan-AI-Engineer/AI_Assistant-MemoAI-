"""
Export module - Output format generation
Task 4: Export & Output
"""
# Lazy imports to handle missing dependencies gracefully
try:
    from src.export.subtitles import SubtitleGenerator
except (ImportError, ModuleNotFoundError) as e:
    SubtitleGenerator = None
    import warnings
    warnings.warn(f"SubtitleGenerator not available: {e}")

try:
    from src.export.documents import DocumentExporter
except (ImportError, ModuleNotFoundError) as e:
    DocumentExporter = None
    import warnings
    warnings.warn(f"DocumentExporter not available: {e}")

try:
    from src.export.tts import TTSSynthesizer
except (ImportError, ModuleNotFoundError) as e:
    TTSSynthesizer = None
    import warnings
    warnings.warn(f"TTSSynthesizer not available: {e}")

try:
    from src.export.batch import BatchExporter
except (ImportError, ModuleNotFoundError) as e:
    BatchExporter = None
    import warnings
    warnings.warn(f"BatchExporter not available: {e}")

__all__ = [
    'SubtitleGenerator',
    'DocumentExporter',
    'TTSSynthesizer',
    'BatchExporter'
]
