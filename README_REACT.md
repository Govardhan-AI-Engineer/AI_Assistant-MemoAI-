# MemoAI - React Frontend Setup

## Overview

The application has been converted from Tkinter to React frontend with FastAPI backend.

## Architecture

```
Frontend (React)          Backend (FastAPI)
     |                            |
     |  HTTP/REST API             |
     |<-------------------------->|
     |                            |
     |                            Database (SQLite)
     |                            |
```

## Setup Instructions

### 1. Backend Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run FastAPI server
python run_api.py
```

Backend will run on: `http://localhost:8000`

### 2. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies
npm install

# Start React development server
npm run dev
```

Frontend will run on: `http://localhost:3000`

## Features

### ✅ Authentication
- User registration
- User login
- Session management (localStorage)
- User isolation

### ✅ Transcription
- File upload transcription
- URL transcription (YouTube, podcasts)
- Language selection or auto-detect
- Real-time progress

### ✅ Translation
- Multi-language translation
- Multiple translation providers (Google, LibreTranslate, DeepL, AI/Groq)
- Translation modes (whole text, paragraph, line-by-line)
- Paragraph-level re-translation

### ✅ Storage
- All transcripts saved to database
- All translations saved to database
- User-isolated storage
- Immutable documents (never overwritten)

### ✅ Transcripts Management
- View all user transcripts
- Search transcripts
- Access previous transcriptions

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `GET /api/auth/user/{user_id}` - Get user info

### Transcription
- `POST /api/transcribe/file` - Transcribe uploaded file
- `POST /api/transcribe/url` - Transcribe from URL

### Translation
- `POST /api/translate` - Translate transcript

### Storage
- `GET /api/transcripts` - Get user's transcripts
- `GET /api/transcripts/{document_id}` - Get specific transcript

### Search
- `GET /api/search/transcripts` - Search transcripts

### Notes
- `POST /api/notes/generate` - Generate AI note
- `GET /api/notes` - Get notes

### Tags
- `GET /api/tags` - Get user's tags
- `POST /api/tags` - Create tag

### Export
- `POST /api/export/subtitles` - Export subtitles

## Development

### Backend Development
```bash
# Run with auto-reload
python run_api.py
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Build for Production
```bash
cd frontend
npm run build
```

## Environment Variables

Create `.env` file in project root:

```env
# Database
DATABASE_URL=sqlite:///data/memoai.db

# Groq API (for AI Translation)
GROQ_API_KEY=your_groq_api_key_here

# DeepL API (optional)
DEEPL_API_KEY=your_deepl_api_key_here
```

## Project Structure

```
AI_Media_Assistant/
├── src/
│   ├── api/              # FastAPI backend
│   │   └── main.py
│   ├── auth/             # Authentication
│   ├── memory/           # Database storage
│   ├── transcription/    # Transcription service
│   ├── translation/      # Translation service
│   └── export/           # Export services
├── frontend/              # React frontend
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
├── data/                 # Data storage
│   ├── memoai.db        # SQLite database
│   └── transcripts/     # File backups
└── requirements.txt
```

## Next Steps

1. Complete Task 2: Multilingual RAG
2. Add more React components for:
   - Notes generation UI
   - Tag management UI
   - Search interface
   - Export options UI
