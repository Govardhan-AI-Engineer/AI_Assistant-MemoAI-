# GUI Export Features - Usage Guide

## Overview

The GUI now includes export functionality for subtitles, documents, and speech synthesis. All export buttons are available after transcription is complete.

## Export Buttons Location

After transcribing audio/video, you'll see an **"📤 Export"** section with three buttons:

1. **📝 Generate Subtitles (SRT/VTT)**
2. **📄 Export Documents (MD/TXT/JSON)**
3. **🔊 Generate Speech (TTS)**

## How to Use

### 1. Generate Subtitles (SRT/VTT)

**Steps:**
1. Complete transcription (or transcription + translation)
2. Click **"📝 Generate Subtitles (SRT/VTT)"**
3. Choose:
   - **Yes**: Export translated subtitles (if translation exists)
   - **No**: Export original subtitles
   - **Cancel**: Abort

**Output:**
- `data/exports/subtitles/[filename].srt`
- `data/exports/subtitles/[filename].vtt`

**Features:**
- Preserves timestamps from transcription
- Supports original or translated text
- Standards-compliant SRT and VTT formats

### 2. Export Documents (MD/TXT/JSON)

**Steps:**
1. Complete transcription (or transcription + translation)
2. Click **"📄 Export Documents (MD/TXT/JSON)"**
3. Choose:
   - **Yes**: Export translated documents (if translation exists)
   - **No**: Export original documents
   - **Cancel**: Abort

**Output:**
- `data/exports/documents/[filename].md` - Markdown with headings and timestamps
- `data/exports/documents/[filename].txt` - Plain text
- `data/exports/documents/[filename].json` - Structured JSON with metadata

**Features:**
- Markdown includes metadata and timestamps
- JSON includes full transcription data with segments/paragraphs
- Supports both original and translated outputs

### 3. Generate Speech (TTS)

**Steps:**
1. Complete transcription (or transcription + translation)
2. Click **"🔊 Generate Speech (TTS)"**
3. Choose:
   - **Yes**: Generate from translated text (if translation exists)
   - **No**: Generate from original text
   - **Cancel**: Abort
4. Enter language code (e.g., 'en', 'hi', 'te') if using original text
5. Choose:
   - **Yes**: One audio file per paragraph
   - **No**: Single audio file (entire text)

**Output:**
- `data/exports/audio/[filename].mp3` - Single file
- OR `data/exports/audio/[filename]_para_1.mp3`, `_para_2.mp3`, etc. - Per paragraph

**Features:**
- Uses gTTS (Google Text-to-Speech) by default
- Falls back to pyttsx3 if gTTS unavailable
- Supports multiple languages
- Configurable: single file or per-paragraph

## Export Workflow Examples

### Example 1: Export Original Subtitles
1. Transcribe video → Get transcription
2. Click "Generate Subtitles"
3. Select "No" (use original)
4. Files created: `video.srt` and `video.vtt`

### Example 2: Export Translated Documents
1. Transcribe video → Get transcription
2. Translate to English
3. Click "Export Documents"
4. Select "Yes" (use translation)
5. Files created: `video.md`, `video.txt`, `video.json` (all with English translation)

### Example 3: Generate Speech from Translation
1. Transcribe Hindi video → Get transcription
2. Translate to English
3. Click "Generate Speech"
4. Select "Yes" (use translation)
5. Select "No" (single file)
6. File created: `video.mp3` (English speech)

## Export File Locations

All exports are saved in:
```
AI_Media_Assistant/
└── data/
    └── exports/
        ├── subtitles/      # SRT and VTT files
        ├── documents/      # MD, TXT, JSON files
        └── audio/          # MP3/WAV files
```

## File Naming

- **With source file**: Uses source file name (e.g., `video.mp4` → `video.srt`)
- **Without source file**: Uses timestamp (e.g., `subtitle_20241201_143022.srt`)

## Status Messages

After each export:
- ✅ Success message with file paths
- Status label shows export result
- Progress bar indicates completion

## Requirements

### For Subtitles & Documents
- ✅ No additional requirements (uses standard library)

### For Speech (TTS)
- ✅ `gtts>=2.4.0` OR `pyttsx3>=2.90`
- ✅ `pydub>=0.25.1` (for format conversion)

All packages are already in `requirements.txt`.

## Tips

1. **Translation First**: For best results, translate first, then export translated versions
2. **Multiple Translations**: You can export each translation separately
3. **Per-Paragraph TTS**: Useful for long texts or when you need separate audio segments
4. **File Organization**: All exports are automatically organized in `data/exports/`

## Troubleshooting

### TTS Not Working
- Install: `pip install gtts>=2.4.0` or `pip install pyttsx3>=2.90`
- Check internet connection (for gTTS)

### Export Buttons Disabled
- Complete transcription first
- Buttons enable automatically after transcription

### Files Not Found
- Check `data/exports/` directory
- Files are organized by type (subtitles/, documents/, audio/)

---

**Export features are now fully integrated into the GUI!** 🎉
