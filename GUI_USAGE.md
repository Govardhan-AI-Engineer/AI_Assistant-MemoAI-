# Transcription GUI - User Guide

## Overview

A simple, user-friendly GUI for transcribing audio/video files and URLs with language selection.

## Features

✅ **File Selection**: Browse and select audio/video files  
✅ **URL Support**: Transcribe from YouTube, podcasts, and direct media URLs  
✅ **Language Selection**: Choose from 90+ languages or use auto-detect  
✅ **Smart Optimization**: Selecting a language skips auto-detection (50% faster!)  
✅ **Robust Pipeline**: Automatic preprocessing, validation, and quality checks  
✅ **Real-time Progress**: See transcription progress in real-time  
✅ **Quality Reports**: View quality scores and warnings  

## How to Run

### Option 1: Direct Launch
```bash
python run_gui.py
```

### Option 2: From Python
```python
from src.ui import main
main()
```

## Usage Guide

### Step 1: Select Input Source

**For Files:**
1. Select "📁 File (Video/Audio)" radio button
2. Click "Browse..." to select your file
3. Supported formats: MP4, MP3, M4A, AAC, WAV, FLAC, OGG, AVI, MOV, MKV, WebM

**For URLs:**
1. Select "🔗 URL (YouTube/Podcast)" radio button
2. Paste your URL in the text field
3. Supports YouTube videos, Shorts, podcasts, and direct media URLs

### Step 2: Select Language

**Option A: Select Specific Language (Recommended - Faster)**
1. Click the language dropdown
2. Select your language from the list
3. Popular languages are shown first
4. **Benefit**: Skips auto-detection pass (50% faster!)

**Option B: Auto-detect (Slower)**
1. Select "Auto-detect (slower)" from dropdown
2. System will detect language automatically
3. Takes longer but useful when language is unknown

### Step 3: Configure Options (Optional)

- **🔧 Enable Audio Preprocessing**: 
  - Noise reduction, normalization, channel fixing
  - Recommended for noisy audio
  - Default: Enabled

- **✅ Enable Validation**: 
  - Quality checks, corruption detection
  - Recommended for all use cases
  - Default: Enabled

- **📝 Paragraph Format**: 
  - Format output into paragraphs
  - Useful for long transcriptions
  - Default: Disabled

### Step 4: Start Transcription

1. Click "🚀 Start Transcription" button
2. Watch progress in real-time
3. Results appear in the output area when complete

## Understanding Results

### Output Information

- **Language**: Detected or selected language
- **Model Used**: Whisper model used (tiny/base/small/medium/large)
- **Preprocessing**: Whether audio preprocessing was applied
- **Validation**: Whether quality validation was performed
- **Quality Score**: 0-100 score (higher is better)

### Quality Warnings

If you see warnings:
- **Repetition detected**: Model may be too small, try larger model
- **Wrong script**: Language mismatch, verify language selection
- **Low confidence**: Audio quality may be poor

### Saved Files

Transcriptions are automatically saved to:
- `data/transcripts/[filename].json` - Full transcription with metadata
- `data/transcripts/[filename].txt` - Plain text version

## Tips for Best Results

### 1. **Always Select Language When Known**
- Saves 50% processing time
- More accurate results
- Better model selection

### 2. **Use Preprocessing for Noisy Audio**
- Reduces background noise
- Normalizes volume
- Improves accuracy

### 3. **Enable Validation**
- Catches quality issues early
- Provides feedback
- Ensures reliable output

### 4. **For Telugu/Hindi/Indian Languages**
- System automatically uses appropriate model
- Telugu → Large model (best quality)
- Other Indian languages → Medium model

## Troubleshooting

### "Invalid URL" Error
- Check URL format
- Ensure URL is accessible
- Try downloading manually first

### "File not found" Error
- Verify file path is correct
- Check file permissions
- Ensure file format is supported

### Poor Quality Results
- Enable preprocessing
- Try larger model
- Check audio quality
- Verify language selection

### Slow Processing
- Select language instead of auto-detect
- Disable preprocessing (if audio is clean)
- Use smaller model (if acceptable quality)

## Language Codes Reference

Popular languages in the dropdown:
- `en` - English
- `te` - Telugu (తెలుగు)
- `hi` - Hindi (हिंदी)
- `ta` - Tamil (தமிழ்)
- `kn` - Kannada (ಕನ್ನಡ)
- `ml` - Malayalam (മലയാളം)
- `zh` - Chinese (中文)
- `ja` - Japanese (日本語)
- `ko` - Korean (한국어)
- `ar` - Arabic (العربية)
- `de` - German (Deutsch)
- `fr` - French (Français)
- `es` - Spanish (Español)
- `ru` - Russian (Русский)

Full list of 90+ languages available in dropdown.

## Technical Details

### Performance Optimization

When language is provided:
- ✅ Skips auto-detection pass (1 transcription instead of 2)
- ✅ Faster model selection
- ✅ More accurate results
- ✅ Lower computational cost

### Robust Pipeline Features

- **Audio Preprocessing**: Noise reduction, normalization, channel fixing
- **Audio Validation**: Corruption detection, completeness checks
- **Intelligent Model Selection**: Language-aware, quality-aware
- **Output Quality Validation**: Repetition detection, script validation
- **Automatic Retry**: Progressive model upgrades if needed

## Examples

### Example 1: Telugu Video File
1. Select "File" → Browse → Select `telugu_video.mp4`
2. Select language: "te - Telugu (తెలుగు)"
3. Enable preprocessing and validation
4. Click "Start Transcription"
5. Result: Fast, accurate Telugu transcription

### Example 2: YouTube URL (Auto-detect)
1. Select "URL" → Paste YouTube URL
2. Select language: "Auto-detect (slower)"
3. Enable all options
4. Click "Start Transcription"
5. Result: Language detected automatically, then transcribed

### Example 3: Noisy Audio
1. Select "File" → Browse → Select `noisy_audio.mp3`
2. Select language: "hi - Hindi (हिंदी)"
3. **Important**: Enable preprocessing
4. Enable validation
5. Click "Start Transcription"
6. Result: Clean transcription despite noise

## Support

For issues or questions:
- Check quality reports in output
- Review warnings and errors
- Try different model sizes
- Verify language selection
