# Translation Module - Complete Documentation

## Overview

The Translation Module provides a robust, multi-provider translation system with automatic fallback, quality refinement, and flexible granularity options.

## Architecture

### Clean Modular Design

```
TranslationService (Main Interface)
    ↓
TranslationOrchestrator (Fallback Logic)
    ↓
TranslationProvider (Base Interface)
    ├── GoogleTranslateProvider
    ├── LibreTranslateProvider
    └── DeepLProvider
```

## Features

### ✅ Multi-Provider Support
- **Google Translate**: Free, no API key required
- **LibreTranslate**: Open-source, self-hosted or public API
- **DeepL**: Free tier with API key

### ✅ Automatic Fallback
- Tries providers in priority order
- Falls back automatically on failure/timeout/corruption
- Validates output quality

### ✅ Translation Granularity
- **Paragraph-level**: Translate full blocks
- **Line-by-line**: Translate line by line (for subtitles)

### ✅ Quality Refinement
- Optional re-translation with secondary provider
- Output validation
- Quality improvement without hallucination

### ✅ Configuration
- Provider priority configurable
- API keys from environment variables
- Easy to extend with new providers

## Quick Start

### Basic Usage

```python
from src.translation import TranslationService, TranslationGranularity

# Initialize service
service = TranslationService()

# Translate text
result = service.translate(
    text="Hello, world!",
    target_language='es',
    source_language='en'
)

print(result['text'])  # "¡Hola, mundo!"
print(result['provider'])  # "google"
```

### Paragraph-Level Translation

```python
text = """
This is the first paragraph.
It contains multiple sentences.

This is the second paragraph.
It also has multiple sentences.
"""

result = service.translate(
    text=text,
    target_language='fr',
    granularity=TranslationGranularity.PARAGRAPH
)
```

### Line-by-Line Translation (for Subtitles)

```python
subtitle_text = "Line 1\nLine 2\nLine 3"

result = service.translate(
    text=subtitle_text,
    target_language='hi',
    granularity=TranslationGranularity.LINE_BY_LINE
)
```

### With Fallback

```python
# Will try DeepL first, fallback to Google if unavailable
service = TranslationService(
    provider_priority=['deepl', 'google', 'libre']
)

result = service.translate(
    text="Test",
    target_language='de',
    preferred_provider='deepl'
)
```

### Re-translation for Quality

```python
service = TranslationService(enable_retranslation=True)

result = service.translate(
    text="Complex text",
    target_language='ja',
    enable_retranslation=True
)

if result['secondary_provider']:
    print(f"Refined with {result['secondary_provider']}")
```

## Integration with Transcription

### Translate Transcription Result

```python
from src.translation.integration import TranscriptionTranslationIntegration

integration = TranscriptionTranslationIntegration()

# Translate transcription
translation = integration.translate_transcription(
    transcription_result={
        'text': 'Transcribed text in Telugu',
        'language': 'te'
    },
    target_language='en'
)

print(translation['translated_text'])
```

### Translate Segments (for Subtitles)

```python
segments = [
    {'text': 'Segment 1', 'start': 0.0, 'end': 5.0},
    {'text': 'Segment 2', 'start': 5.0, 'end': 10.0}
]

translated_segments = integration.translate_segments(
    segments=segments,
    target_language='en'
)
```

## Configuration

### Environment Variables

```bash
# DeepL API key (optional)
DEEPL_API_KEY=your_api_key

# LibreTranslate API key (optional)
LIBRETRANSLATE_API_KEY=your_api_key

# LibreTranslate API URL (optional, defaults to public API)
LIBRETRANSLATE_API_URL=https://your-instance.com/translate

# Provider priority (comma-separated)
TRANSLATION_PROVIDER_PRIORITY=google,libre,deepl

# Enable re-translation
ENABLE_RETRANSLATION=true
```

### Code Configuration

```python
# Custom provider priority
service = TranslationService(
    provider_priority=['google', 'libre', 'deepl']
)

# Disable re-translation
service = TranslationService(enable_retranslation=False)
```

## Provider Details

### Google Translate
- **Cost**: Free
- **API Key**: Not required
- **Rate Limits**: Built-in rate limiting
- **Best For**: General purpose, reliable

### LibreTranslate
- **Cost**: Free (open-source)
- **API Key**: Optional (for self-hosted)
- **Best For**: Privacy-focused, self-hosted option

### DeepL
- **Cost**: Free tier available
- **API Key**: Required
- **Best For**: High quality translations

## Error Handling

The module handles errors gracefully:

- **Provider Unavailable**: Falls back to next provider
- **Timeout**: Falls back to next provider
- **Corrupted Output**: Falls back to next provider
- **All Providers Fail**: Raises `TranslationError`

## Extending with New Providers

To add a new provider:

1. Create a new class inheriting from `TranslationProvider`
2. Implement required methods
3. Add to `TranslationOrchestrator.providers` dictionary
4. Add to provider priority list

Example:

```python
class MyCustomProvider(TranslationProvider):
    @property
    def name(self) -> str:
        return "My Custom Provider"
    
    @property
    def is_available(self) -> bool:
        # Check availability
        return True
    
    def translate(self, text, target_language, source_language=None):
        # Implement translation
        return translated_text
    
    def translate_batch(self, texts, target_language, source_language=None):
        # Implement batch translation
        return translated_texts
```

## Best Practices

1. **Always specify source language** when known (more accurate)
2. **Use paragraph-level** for general text
3. **Use line-by-line** for subtitles/SRT/VTT
4. **Enable re-translation** for important content
5. **Configure provider priority** based on your needs
6. **Handle exceptions** gracefully in production

## Examples

See `examples/translation_examples.py` for comprehensive examples including:
- Paragraph translation
- Line-by-line translation
- Fallback mechanism
- Re-translation
- Batch translation
- Provider information

## Testing

Run examples:

```bash
python examples/translation_examples.py
```

## Support

For issues:
- Check provider availability
- Verify API keys (if required)
- Check network connectivity
- Review error messages

## Next Steps

The translation module is ready for use with:
- Transcription results
- Subtitle files
- Standalone text translation
- Integration with export module (Task 4)
