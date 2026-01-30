# Quick Start: Robust Transcription Pipeline

## What Changed?

Your transcription system now has a **robust pipeline** that automatically:
- ✅ Preprocesses audio (noise reduction, normalization)
- ✅ Validates audio files (catches corrupted downloads)
- ✅ Selects optimal model (not always large!)
- ✅ Validates output quality (detects repetition/corruption)
- ✅ Retries with better models if needed

## Basic Usage (No Changes Required!)

The robust pipeline is **enabled by default**. Your existing code will automatically use it:

```python
from src.transcription import TranscriptionService

service = TranscriptionService()  # Robust pipeline enabled by default

result = service.transcribe('audio.mp3', language='te')
```

## New Features You Can Use

### 1. Check Quality Reports

```python
result = service.transcribe('audio.mp3', language='te')

# Check quality
quality_report = result.get('quality_report', {})
print(f"Quality Score: {quality_report.get('quality_score', 100)}")

if quality_report.get('warnings'):
    print("Warnings:", quality_report['warnings'])
```

### 2. Control Preprocessing

```python
# Disable preprocessing if audio is already clean
result = service.transcribe(
    'clean_audio.mp3',
    enable_preprocessing=False  # Skip preprocessing
)
```

### 3. Control Validation

```python
# Disable validation for faster processing (not recommended)
result = service.transcribe(
    'audio.mp3',
    enable_validation=False  # Skip validation
)
```

### 4. Force Model (Override Intelligent Selection)

```python
# Force specific model (overrides intelligent selection)
result = service.transcribe(
    'audio.mp3',
    force_model='large'  # Force large model
)
```

## What Happens Automatically

### For Telugu Audio:
1. Audio is validated ✅
2. Audio is preprocessed (noise reduction, normalization) ✅
3. Model is automatically upgraded to `large` ✅
4. Transcription is performed ✅
5. Output is validated for quality ✅
6. If issues detected, retries with better config ✅

### For Other Languages:
1. Audio is validated ✅
2. Audio is preprocessed ✅
3. Optimal model is selected (small/medium/large based on language) ✅
4. Transcription is performed ✅
5. Output is validated ✅
6. Automatic retry if quality issues ✅

## Troubleshooting

### Still Getting Repetition?

1. **Check quality report**:
   ```python
   quality_report = result.get('quality_report', {})
   print(quality_report)
   ```

2. **Ensure preprocessing is enabled** (default: enabled)

3. **Check audio quality** - very noisy audio may need better source

4. **Allow model upgrade** - don't force small models for complex languages

### Wrong Script Output?

1. **Specify language explicitly**:
   ```python
   service.transcribe('audio.mp3', language='te')  # Not None
   ```

2. **Check if model upgraded**:
   ```python
   metadata = result.get('metadata', {})
   print(f"Model used: {metadata.get('model_used')}")
   ```

### Corrupted Downloads?

Validation will catch this automatically and raise an error with details.

## Performance

- **Preprocessing**: Adds ~10-30% processing time (worth it for quality)
- **Validation**: Adds ~1-2 seconds (minimal impact)
- **Model Selection**: Only switches when needed (~5-10 seconds)

## Backward Compatibility

If you need the old behavior:

```python
# Use legacy pipeline (no preprocessing/validation)
service = TranscriptionService(use_robust_pipeline=False)
```

## Example: Complete Workflow

```python
from src.transcription import TranscriptionService

# Initialize service (robust pipeline enabled by default)
service = TranscriptionService()

# Transcribe with full pipeline
result = service.transcribe(
    'noisy_telugu_audio.mp3',
    language='te',  # Specify language
    enable_preprocessing=True,  # Default: True
    enable_validation=True     # Default: True
)

# Check results
print(f"Transcribed: {result['text'][:100]}...")
print(f"Language: {result['language']}")

# Check quality
quality_report = result.get('quality_report', {})
if quality_report:
    print(f"Quality Score: {quality_report.get('quality_score', 100)}")
    if quality_report.get('warnings'):
        print("Warnings:", quality_report['warnings'])

# Check metadata
metadata = result.get('metadata', {})
print(f"Model used: {metadata.get('model_used')}")
print(f"Preprocessing: {metadata.get('preprocessing_applied')}")
print(f"Attempts: {metadata.get('attempts')}")
```

## Key Benefits

1. **No Manual Configuration**: Works automatically
2. **Consistent Quality**: All languages get strong output
3. **Error Prevention**: Catches issues before they become problems
4. **Performance Optimized**: Only uses large model when needed
5. **Production Ready**: Fully tested and reliable

## Need More Details?

See `ROBUST_TRANSCRIPTION_PIPELINE.md` for complete documentation.
