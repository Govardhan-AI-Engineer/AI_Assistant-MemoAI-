# Robust Translation Pipeline for Code-Mixed Multilingual Speech

## Overview

This document describes the robust translation pipeline designed specifically for handling code-mixed multilingual speech, especially Indian languages mixed with English (Hinglish, Tenglish, etc.).

## Problem Statement

Traditional translation services struggle with:
- **Code-mixed speech**: Hindi + English (Hinglish), Telugu + English (Tenglish)
- **Filler words**: "na", "ji", "baivi", "anna", etc.
- **Transliterated words**: Hindi words written in English script
- **Poor sentence boundaries**: Missing or incorrect punctuation
- **Grammar collapse**: When translating whole paragraphs, context is lost
- **Untranslated words**: Some words remain in source language

## Solution Architecture

The robust translation pipeline implements a multi-stage approach:

```
Raw Transcription
    ↓
[1] Text Normalization
    - Fix sentence boundaries
    - Remove filler words
    - Handle code-mixed patterns
    ↓
[2] Sentence Splitting
    - Split into individual sentences
    - Preserve context within sentences
    ↓
[3] Sentence-by-Sentence Translation
    - Translate each sentence with explicit source language
    - Force source language (no auto-detect)
    - Multi-provider fallback
    ↓
[4] Optional LLM Refinement
    - Fix grammar and readability
    - Preserve original meaning
    ↓
Final Translation
```

## Components

### 1. Text Normalizer (`src/translation/text_normalizer.py`)

**Purpose**: Normalize transcription text before translation

**Features**:
- **Sentence boundary fixing**: Ensures proper punctuation
- **Filler word removal**: Removes language-specific fillers (na, ji, baivi, anna, etc.)
- **Code-mixed handling**: Normalizes mixed language patterns
- **Whitespace cleanup**: Removes extra spaces and newlines

**Usage**:
```python
from src.translation.text_normalizer import TextNormalizer

normalizer = TextNormalizer(source_language='hi')
normalized = normalizer.normalize(
    text,
    remove_fillers=True,
    fix_sentences=True,
    handle_code_mixed=True
)
```

**Supported Languages**:
- Hindi (`hi`)
- Telugu (`te`)
- Tamil (`ta`)
- Kannada (`kn`)
- Malayalam (`ml`)
- English (`en`)

### 2. Robust Translator (`src/translation/robust_translator.py`)

**Purpose**: Main translation service with sentence-by-sentence processing

**Features**:
- **Explicit source language**: No auto-detection (more accurate)
- **Sentence-by-sentence translation**: Prevents semantic bleed
- **Text normalization**: Automatic before translation
- **Two-step translation**: Normalize first, then translate
- **Optional LLM refinement**: Grammar and readability fixes

**Usage**:
```python
from src.translation.robust_translator import RobustTranslator

translator = RobustTranslator(
    enable_normalization=True,
    enable_llm_refinement=False  # Set to True if LLM available
)

result = translator.translate(
    text="Brother, how much time na ji baivi...",
    target_language='en',
    source_language='hi',  # REQUIRED - no auto-detect
    use_sentence_by_sentence=True
)
```

### 3. Robust Integration (`src/translation/robust_integration.py`)

**Purpose**: Integration layer for transcription results

**Usage**:
```python
from src.translation.robust_integration import RobustTranscriptionTranslationIntegration

integration = RobustTranscriptionTranslationIntegration(
    enable_normalization=True,
    enable_llm_refinement=False
)

transcription_result = {
    'text': '...',
    'language': 'hi'
}

result = integration.translate_transcription(
    transcription_result=transcription_result,
    target_language='en',
    use_sentence_by_sentence=True,
    use_two_step=False
)
```

### 4. LLM Refiner (`src/translation/llm_refiner.py`)

**Purpose**: Optional grammar and readability refinement using free/open-source LLMs

**Features**:
- **Grammar fixes**: Corrects grammatical errors
- **Readability improvement**: Makes text more natural
- **Content preservation**: Does NOT add, remove, or invent content
- **Free/open-source only**: Uses local models (LLaMA, Mistral, etc.)

**Status**: Placeholder implementation - requires LLM library setup

## Translation Providers

The pipeline supports multiple providers with automatic fallback:

1. **Google Translate** (via `deep-translator`)
2. **LibreTranslate** (free, self-hosted option)
3. **DeepL** (requires API key)

**Fallback Strategy**:
- Try preferred provider first
- If fails, try next available provider
- Continue until success or all providers exhausted

## Usage Examples

### Example 1: Basic Translation

```python
from src.translation.robust_integration import RobustTranscriptionTranslationIntegration

# Initialize
integration = RobustTranscriptionTranslationIntegration(
    enable_normalization=True
)

# Transcription result (from Whisper)
transcription = {
    'text': 'Brother, how much time will it take to reach the south? Anna first coconut drink water na ji baivi south aagaya baivi how do you know?',
    'language': 'hi'
}

# Translate
result = integration.translate_transcription(
    transcription_result=transcription,
    target_language='en',
    use_sentence_by_sentence=True
)

print(result['translated_text'])
```

### Example 2: Two-Step Translation

```python
from src.translation.robust_translator import RobustTranslator

translator = RobustTranslator(enable_normalization=True)

# Two-step: normalize first, then translate
result = translator.translate_two_step(
    text="...",
    target_language='en',
    source_language='hi'
)
```

### Example 3: With Provider Selection

```python
result = integration.translate_transcription(
    transcription_result=transcription,
    target_language='en',
    preferred_provider='google',  # or 'libre', 'deepl'
    use_sentence_by_sentence=True
)
```

## GUI Integration

The GUI automatically uses the robust translator when available. It:
- Uses sentence-by-sentence translation by default
- Shows normalization status
- Displays provider information and fallback status
- Handles both robust and standard translators (fallback)

## Configuration

### Enable/Disable Normalization

```python
integration = RobustTranscriptionTranslationIntegration(
    enable_normalization=True  # Set to False to disable
)
```

### Enable LLM Refinement

```python
integration = RobustTranscriptionTranslationIntegration(
    enable_normalization=True,
    enable_llm_refinement=True,
    llm_model='llama3'  # or 'mistral', etc.
)
```

**Note**: LLM refinement requires:
- LLM library installed (e.g., `llama-cpp-python`, `transformers`, `ollama`)
- Model downloaded and configured
- See `src/translation/llm_refiner.py` for implementation details

## Key Differences from Standard Translator

| Feature | Standard Translator | Robust Translator |
|---------|-------------------|-------------------|
| Source Language | Optional (auto-detect) | **Required** (explicit) |
| Text Normalization | No | **Yes** (filler removal, etc.) |
| Translation Method | Whole text / Paragraph / Line | **Sentence-by-sentence** |
| Code-Mixed Handling | Limited | **Comprehensive** |
| LLM Refinement | No | **Optional** |
| Sentence Boundaries | Not fixed | **Fixed before translation** |

## Best Practices

1. **Always provide source language**: Don't rely on auto-detection
2. **Use sentence-by-sentence**: Better quality for code-mixed speech
3. **Enable normalization**: Especially for transcribed speech
4. **Handle errors gracefully**: Check for fallback provider usage
5. **Test with real data**: Use actual code-mixed transcriptions

## Troubleshooting

### Issue: Untranslated words remain

**Solution**: 
- Ensure source language is explicitly set
- Enable normalization
- Use sentence-by-sentence translation

### Issue: Poor grammar in output

**Solution**:
- Enable LLM refinement (if available)
- Use two-step translation
- Try different provider

### Issue: Text repetition

**Solution**:
- This is usually a display issue, not translation
- Check GUI display logic
- Ensure translation is only called once

## Future Enhancements

1. **Better code-mixed detection**: Automatic detection of code-mixed patterns
2. **Language-specific normalization**: More language-specific rules
3. **Context-aware translation**: Use surrounding sentences for better context
4. **Quality scoring**: Score translation quality and retry if low
5. **Custom filler word lists**: Allow user-defined filler words

## Files

- `src/translation/text_normalizer.py` - Text normalization
- `src/translation/robust_translator.py` - Robust translation service
- `src/translation/robust_integration.py` - Integration layer
- `src/translation/llm_refiner.py` - LLM-based refinement
- `example_robust_translation.py` - Usage examples

## Dependencies

Required:
- `deep-translator>=1.11.4` (for Google Translate)
- `googletrans==4.0.0rc1` (optional, fallback)

Optional:
- LLM library (for refinement): `llama-cpp-python`, `transformers`, or `ollama`

## License

Same as main project.
