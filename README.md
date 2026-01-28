# MemoAI - AI Assistant Memory

AI-powered application for converting video and audio content into translated text, subtitles, and structured notes.

## Features

- 🎤 **Audio/Video Transcription**: Support for MP4, MP3, AAC, M4A formats
- 🌐 **Online Media**: YouTube and podcast URL transcription
- 🌍 **Multi-language Translation**: Multiple translation services with quality refinement
- 📝 **Subtitle Generation**: SRT and VTT format export
- 📄 **Document Export**: Markdown and other documentation formats
- 🔊 **Speech Synthesis**: Translated audio dubbing
- 💾 **Context & Memory**: Persistent storage, search, and note organization

## Project Status

This project is divided into 5 tasks. See `PROJECT_TASKS.md` for detailed breakdown.

### ✅ Task 1: Core Transcription Module - COMPLETED
- Local file transcription (MP4, MP3, AAC, M4A)
- **Whisper integration** (free, open-source STT)
- Paragraph-level output formatting
- See `TASK1_README.md` for details

### 🔄 Task 2-3: Pending
### 📋 Task 4: Export & Output with Advanced RAG for QA - Updated
### 🔄 Task 5: Pending

## Architecture

Modular Monolith structure with Python, organized into distinct modules:
- `transcription/` - Speech-to-text processing
- `translation/` - Multi-provider translation
- `export/` - Output format generation
- `memory/` - Context and storage management
- `core/` - Shared utilities

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### Installation
```bash
pip install -r requirements.txt
```

### Basic Usage
```bash
# Transcribe an audio/video file
python main.py path/to/your/audio.mp3

# With paragraph formatting
python main.py path/to/your/video.mp4 --paragraphs

# See all options
python main.py --help
```

See `TASK1_README.md` for detailed usage examples.

## License

MIT
"# AI_Assistant-MemoAI-" 
