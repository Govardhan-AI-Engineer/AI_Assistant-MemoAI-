# Robust Transcription Pipeline - Complete Solution

## Overview

This document describes the comprehensive, language-agnostic transcription pipeline designed to solve transcription quality issues including corrupted output, repetitive Unicode characters, broken words, and missing sentence boundaries, especially in noisy audio or mixed-speaker scenarios.

## Architecture: Modular Monolith

The solution follows a clean modular monolith architecture with the following components:

```
src/transcription/
├── robust_transcriber.py      # Main robust pipeline orchestrator
├── audio_preprocessor.py       # Audio preprocessing (noise reduction, normalization)
├── audio_validator.py          # Audio validation (corruption detection)
├── quality_validator.py        # Output quality validation
├── model_selector.py           # Intelligent model selection
├── transcriber.py              # Core Whisper transcription (existing)
├── audio_extractor.py          # Audio extraction (existing)
├── service.py                  # Service layer (updated to use robust pipeline)
└── ...
```

## Components

### 1. Audio Preprocessor (`audio_preprocessor.py`)

**Purpose**: Automatically preprocesses audio before transcription to improve quality.

**Features**:
- **Noise Reduction**: Uses FFmpeg's `afftdn` (adaptive FFT denoiser) filter
- **Normalization**: Uses `loudnorm` for broadcast-standard volume normalization
- **Channel Fixing**: Converts stereo to mono, fixes channel issues
- **Resampling**: Ensures optimal sample rate (16kHz) for Whisper
- **Quality Detection**: Analyzes audio quality metrics

**FFmpeg Filters Used**:
```bash
# Channel handling
pan=mono|c0=0.5*c0+0.5*c1

# Noise reduction
highpass=f=80                    # Remove low-frequency noise
lowpass=f=12000                  # Remove high-frequency noise
afftdn=nr=0.5                    # Adaptive denoising

# Normalization
loudnorm=I=-16:TP=-1.5:LRA=11   # Broadcast-standard normalization
```

**Usage**:
```python
from src.transcription.audio_preprocessor import AudioPreprocessor

preprocessed_audio, metadata = AudioPreprocessor.preprocess(
    input_path,
    enable_noise_reduction=True,
    enable_normalization=True,
    enable_channel_fix=True
)
```

### 2. Audio Validator (`audio_validator.py`)

**Purpose**: Detects corrupted or incomplete downloads, especially from YouTube Shorts and podcasts.

**Validation Checks**:
1. **File Existence**: Verifies file exists
2. **File Size**: Checks minimum file size (1KB)
3. **FFprobe Validation**: Validates audio stream integrity
4. **Duration Validation**: Checks for reasonable duration
5. **Expected Duration Check**: Compares with expected duration (for downloads)
6. **Silent Audio Detection**: Detects likely silent/corrupted audio

**Usage**:
```python
from src.transcription.audio_validator import AudioValidator

is_valid, report = AudioValidator.validate(
    audio_path,
    expected_duration=expected_duration,
    source='youtube'
)

# For downloads
is_complete, report = AudioValidator.validate_download_completeness(
    audio_path,
    expected_metadata,
    source='youtube'
)
```

### 3. Intelligent Model Selector (`model_selector.py`)

**Purpose**: Selects optimal Whisper model based on language, audio quality, and duration.

**Selection Factors**:
1. **Language Requirements**:
   - `large_required`: Telugu (known issues with smaller models)
   - `medium_recommended`: Indian languages, Asian languages, Slavic languages
   - `small_sufficient`: Western European languages

2. **Audio Quality**: Low quality audio → larger model
3. **Duration**: Very long audio → larger model for consistency
4. **Current Model**: Prefers not to downgrade if already loaded

**Model Hierarchy**: `tiny` < `base` < `small` < `medium` < `large`

**Usage**:
```python
from src.transcription.model_selector import ModelSelector

selected_model, reason = ModelSelector.select_model(
    language='te',
    audio_quality='low',
    duration=300.0,
    current_model='small'
)
```

### 4. Quality Validator (`quality_validator.py`)

**Purpose**: Detects low-confidence or corrupted transcription outputs.

**Validation Checks**:
1. **Repetition Detection**:
   - Compression ratio analysis (Whisper metric)
   - Repeated character patterns (e.g., ुुुु)
   - Repeated word patterns
   - Repeated phrase patterns

2. **Corrupted Unicode Detection**:
   - Excessive combining marks
   - Invalid Unicode sequences
   - Inappropriate script mixing

3. **Missing Boundaries**: Detects missing sentence boundaries

4. **Script Validation**: Validates correct script for language (e.g., Telugu script for Telugu)

5. **Low Confidence Detection**: Analyzes segment confidence scores

**Usage**:
```python
from src.transcription.quality_validator import QualityValidator

is_valid, quality_report = QualityValidator.validate(
    text=transcribed_text,
    language='te',
    compression_ratio=compression_ratio,
    segments=segments
)
```

### 5. Robust Transcriber (`robust_transcriber.py`)

**Purpose**: Main pipeline orchestrator that integrates all components.

**Pipeline Flow**:
1. Extract audio from video (if needed)
2. Validate audio file
3. Preprocess audio (noise reduction, normalization, channel fixing)
4. Select optimal model
5. Transcribe with retry logic
6. Validate output quality
7. Retry with larger model if quality issues detected

**Retry Logic**:
- Maximum 3 retry attempts
- Automatically upgrades model if quality issues detected
- Progressive fallback: `small` → `medium` → `large`

**Usage**:
```python
from src.transcription.robust_transcriber import RobustTranscriber

transcriber = RobustTranscriber(initial_model='base')

result = transcriber.transcribe(
    file_path,
    language='te',
    enable_preprocessing=True,
    enable_validation=True
)
```

## Integration with Service Layer

The `TranscriptionService` has been updated to use the robust pipeline by default:

```python
from src.transcription import TranscriptionService

# Robust pipeline (default)
service = TranscriptionService(use_robust_pipeline=True)

# Legacy pipeline (for backward compatibility)
service = TranscriptionService(use_robust_pipeline=False)
```

## Whisper Configuration Strategies

### Model Selection Strategy

1. **Language-Based**:
   - Telugu → `large` (required)
   - Indian/Asian languages → `medium` (recommended)
   - Western European → `small` (sufficient)

2. **Quality-Based**:
   - Low quality audio → upgrade by 1 level
   - High quality audio → can use smaller models

3. **Duration-Based**:
   - Very long (>1 hour) → use `medium` or `large`
   - Very short (<10 seconds) → can use smaller models

### Decoding Options

**For Medium/Large Models**:
```python
{
    'beam_size': 5,                    # Beam search for accuracy
    'best_of': 5,                      # Multiple candidates
    'condition_on_previous_text': True, # Context awareness
    'compression_ratio_threshold': 2.4, # Repetition detection
    'logprob_threshold': -1.0,         # Confidence threshold
    'no_speech_threshold': 0.6,        # Speech detection
}
```

**For Tiny/Base Models**:
```python
{
    'beam_size': 1,                    # Greedy decoding (faster)
    'best_of': 1,                      # Single candidate
    'condition_on_previous_text': False, # Avoid repetition
}
```

## Fallback and Retry Logic

### Automatic Retry Conditions

1. **Critical Quality Issues**:
   - Repetition detected (compression_ratio > 5.0)
   - Corrupted Unicode patterns
   - Wrong script detected

2. **Low Quality Score**: Quality score < 50

3. **Language Requirements**: Language requires larger model

### Retry Flow

```
Attempt 1: small model
  ↓ (if quality issues)
Attempt 2: medium model
  ↓ (if still issues)
Attempt 3: large model
```

## Best Practices for Multilingual Accuracy

### 1. Always Use Preprocessing
- Reduces noise that confuses models
- Normalizes volume for consistent processing
- Fixes channel issues

### 2. Enable Validation
- Catches corrupted downloads early
- Detects quality issues before they propagate
- Provides feedback for debugging

### 3. Language Specification
- When language is known, specify it explicitly
- Avoids auto-detection errors
- Enables language-specific optimizations

### 4. Model Selection
- Trust the intelligent model selector
- Don't force small models for complex languages
- Allow automatic upgrades

### 5. Quality Monitoring
- Check quality reports in results
- Monitor compression ratios
- Watch for repetition warnings

## Example Usage

### Basic Usage (Robust Pipeline)

```python
from src.transcription import TranscriptionService

service = TranscriptionService(use_robust_pipeline=True)

# Transcribe with automatic preprocessing and validation
result = service.transcribe(
    'audio.mp3',
    language='te',  # Specify language for best results
    enable_preprocessing=True,
    enable_validation=True
)

# Check quality report
quality_report = result.get('quality_report', {})
print(f"Quality Score: {quality_report.get('quality_score', 100)}")
print(f"Warnings: {quality_report.get('warnings', [])}")
```

### Advanced Usage (Direct Robust Transcriber)

```python
from src.transcription.robust_transcriber import RobustTranscriber

transcriber = RobustTranscriber(initial_model='base')

result = transcriber.transcribe(
    'noisy_audio.mp3',
    language='hi',
    enable_preprocessing=True,
    enable_validation=True,
    force_model=None  # Let intelligent selector choose
)

# Access detailed metadata
metadata = result.get('metadata', {})
print(f"Model used: {metadata.get('model_used')}")
print(f"Attempts: {metadata.get('attempts')}")
print(f"Preprocessing applied: {metadata.get('preprocessing_applied')}")
```

## Performance Considerations

### Preprocessing Overhead
- Adds ~10-30% processing time
- Significantly improves quality for noisy audio
- Recommended for all production use

### Model Selection Overhead
- Model switching adds ~5-10 seconds
- Only happens when upgrade is needed
- Worth it for quality improvement

### Validation Overhead
- Audio validation: ~1-2 seconds
- Quality validation: <1 second
- Minimal impact, high value

## Troubleshooting

### Issue: Still Getting Repetition

**Solutions**:
1. Ensure preprocessing is enabled
2. Check audio quality (may need better source)
3. Verify language is specified correctly
4. Allow model to upgrade to `large` if needed

### Issue: Wrong Script Output

**Solutions**:
1. Specify language explicitly
2. Use larger model (medium/large)
3. Check audio quality (noise can confuse models)
4. Enable preprocessing

### Issue: Corrupted Downloads

**Solutions**:
1. Validation will catch this automatically
2. Check network connection
3. Try re-downloading
4. Check source URL validity

## Configuration

All components are configurable via the service:

```python
service = TranscriptionService(
    model_name='base',           # Initial model
    use_robust_pipeline=True     # Enable robust pipeline
)

result = service.transcribe(
    file_path,
    language='te',
    enable_preprocessing=True,   # Audio preprocessing
    enable_validation=True,       # Validation
    force_model=None             # Auto-select or force
)
```

## Conclusion

This robust pipeline ensures:
- ✅ Consistent quality across all languages
- ✅ Automatic handling of noisy audio
- ✅ Detection and prevention of corrupted outputs
- ✅ Intelligent model selection
- ✅ Automatic retry with fallback models
- ✅ Production-ready reliability

The pipeline is fully local, free/open-source, and designed for scale.
