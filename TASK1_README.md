# Task 1: Core Transcription Module - COMPLETED ✅

## Overview
Task 1 implements the core transcription functionality for local audio/video files using **OpenAI Whisper** (free, open-source STT).

## Features Implemented

### ✅ Audio/Video File Support
- **Video formats**: MP4, AVI, MOV, MKV, WebM, FLV
- **Audio formats**: MP3, AAC, M4A, WAV, FLAC, OGG
- Automatic audio extraction from video files using FFmpeg

### ✅ Whisper Integration (Free & Open-Source)
- Support for all Whisper models: tiny, base, small, medium, large
- Configurable model selection via config or CLI
- Auto language detection
- Manual language specification
- Translation capability (translate to English)

### ✅ Paragraph-Level Output
- Configurable word count per paragraph
- Default: 50 words per paragraph (configurable)
- Time-stamped paragraphs with start/end times

### ✅ File Management
- Automatic saving of transcriptions (JSON format)
- Plain text export
- Metadata tracking (source file, creation time, model used)

## Project Structure

```
src/transcription/
├── __init__.py              # Module exports
├── audio_extractor.py       # Audio extraction from video files
├── transcriber.py           # Core Whisper transcription
├── file_handler.py          # Save/load transcription files
└── service.py               # Main transcription service interface
```

## Usage

### Command Line Interface

```bash
# Basic transcription
python main.py path/to/audio.mp3

# With specific model
python main.py path/to/video.mp4 --model small

# With paragraph formatting
python main.py path/to/audio.mp3 --paragraphs --words-per-paragraph 50

# Specify language
python main.py path/to/audio.mp3 --language en

# Don't save to file
python main.py path/to/audio.mp3 --no-save
```

### Python API

```python
from pathlib import Path
from src.transcription import TranscriptionService

# Initialize service
service = TranscriptionService(model_name="base")

# Transcribe file
result = service.transcribe(
    file_path=Path("audio.mp3"),
    language=None,  # Auto-detect
    save_result=True,
    paragraph_format=True,
    words_per_paragraph=50
)

print(result['text'])
print(f"Language: {result['language']}")
print(f"Paragraphs: {len(result['paragraphs'])}")
```

## Configuration

Edit `src/core/config.py` or use environment variables:

```bash
# .env file
WHISPER_MODEL=base              # tiny, base, small, medium, large
PARAGRAPH_WORD_COUNT=50         # Words per paragraph
```

## Requirements

### System Requirements
- **FFmpeg**: Required for video file processing
  - Windows: Download from https://ffmpeg.org/download.html
  - Add to PATH or install via package manager

### Python Dependencies
All dependencies are in `requirements.txt`:
- `openai-whisper` - Speech-to-text
- `torch` & `torchaudio` - Whisper backend
- `ffmpeg-python` - FFmpeg integration

## Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Verify FFmpeg installation
ffmpeg -version
```

## Output Files

Transcriptions are saved to `data/transcripts/`:
- `{filename}.json` - Full transcription with metadata
- `{filename}.txt` - Plain text version

## Example Output

```json
{
  "text": "Full transcription text...",
  "language": "en",
  "paragraphs": [
    {
      "text": "First paragraph text...",
      "start": 0.0,
      "end": 5.2
    }
  ],
  "segments": [...],
  "metadata": {
    "created_at": "2024-01-01T12:00:00",
    "source_file": "audio.mp3",
    "model": "base"
  }
}
```

## Testing

Run the example script:
```bash
python example_usage.py
```

## Next Steps

Task 1 is complete! Ready to proceed to:
- **Task 2**: Online Media Transcription (YouTube, podcasts, SRT/VTT files)

## Notes

- First run will download the Whisper model (may take time)
- Larger models (medium, large) provide better accuracy but are slower
- Video files are automatically converted to audio for processing
- All processing is done locally (no API calls required)
- **Completely free and open-source** - no API keys needed
