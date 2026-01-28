# MemoAI - Project Task Breakdown

## Project Overview
**MemoAI** - AI Assistant Memory: Video-to-text transcription, translation, and intelligent note generation system.

## Architecture: Modular Monolith (Python)

### Project Structure
```
AI_Media_Assistant/
├── src/
│   ├── transcription/          # Task 1 & 2
│   ├── translation/            # Task 3
│   ├── export/                 # Task 4
│   ├── memory/                 # Task 5
│   ├── core/                   # Shared utilities
│   └── api/                    # API layer
├── tests/
├── config/
├── data/                       # Storage for transcripts, notes
└── requirements.txt
```

---

## Task Breakdown (5 Tasks)

### **Task 1: Project Setup & Core Transcription Module**
**Objective**: Set up modular monolith structure and implement local file transcription

**Deliverables**:
- Project structure with modular monolith architecture
- Core transcription module for local files (MP4, MP3, AAC, M4A)
- Audio extraction from video files
- Integration with free STT models (Whisper via OpenAI Whisper or Hugging Face)
- Basic configuration management
- Model selection for paragraph-level output (adjustable word counts)

**Free Resources**:
- OpenAI Whisper (open-source, free)
- Hugging Face Transformers
- FFmpeg for audio extraction

**Estimated Duration**: 2-3 days

---

### **Task 2: Online Media Transcription**
**Objective**: Extend transcription to support online sources and subtitle files

**Deliverables**:
- YouTube URL transcription (using yt-dlp)
- Podcast URL transcription
- SRT/VTT subtitle file parsing and handling
- Translation-only workflow for existing subtitles
- URL validation and media extraction

**Free Resources**:
- yt-dlp (YouTube downloader)
- requests library for podcast URLs
- pysrt for SRT parsing

**Estimated Duration**: 2-3 days

---

### **Task 3: Translation Module**
**Objective**: Implement multi-provider translation with quality refinement

**Deliverables**:
- Integration with free translation services:
  - Google Translate API (free tier)
  - LibreTranslate (open-source, self-hosted option)
  - DeepL (free tier if available)
- Paragraph-level translation
- Line-by-line translation options
- Re-translation capability for quality refinement
- Translation service fallback mechanism

**Free Resources**:
- googletrans (Python library)
- LibreTranslate API
- DeepL free tier

**Estimated Duration**: 2-3 days

---

### **Task 4: Export & Output Module with Advanced RAG for QA**
**Objective**: Generate multiple output formats, speech synthesis, and implement Advanced RAG for user question-answering

**Deliverables**:
- SRT subtitle file generation
- VTT subtitle file generation
- Markdown export with formatting
- Other documentation formats (TXT, JSON)
- Speech synthesis for translated audio dubbing
- Batch export capabilities
- **Advanced RAG (Retrieval-Augmented Generation) system for QA**:
  - Vector embeddings for transcribed content
  - Semantic search across transcripts
  - Context-aware question answering
  - Multi-document retrieval
  - Citation and source tracking

**Free Resources**:
- gTTS (Google Text-to-Speech) or pyttsx3
- pydub for audio manipulation
- Sentence Transformers (free embeddings)
- FAISS or ChromaDB (vector database)
- LangChain (optional, for RAG pipeline)

**Estimated Duration**: 3-4 days

---

### **Task 5: Context & Memory Module**
**Objective**: Build persistent context management and search system

**Deliverables**:
- Persistent storage for transcripts and notes (SQLite/JSON)
- Multi-session workflow support
- Search and retrieval across transcribed content
- Note organization system
- Tagging system for content categorization
- Context persistence across sessions

**Free Resources**:
- SQLite for local database
- SQLAlchemy ORM
- Full-text search capabilities

**Estimated Duration**: 2-3 days

---

## Technology Stack (Free Resources)

### Core Libraries
- **Python 3.9+**
- **Whisper** (OpenAI) - Speech-to-text
- **FFmpeg** - Audio/video processing
- **yt-dlp** - YouTube/podcast download
- **googletrans** / **LibreTranslate** - Translation
- **gTTS** / **pyttsx3** - Text-to-speech
- **SQLite** - Database
- **FastAPI** / **Flask** - API framework (optional)

### Development Tools
- **pytest** - Testing
- **black** - Code formatting
- **pylint** - Linting

---

## Next Steps
We'll start with **Task 1** and complete each task sequentially.
