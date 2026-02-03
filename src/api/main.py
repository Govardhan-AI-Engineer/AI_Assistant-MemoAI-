"""
FastAPI main application
Backend API for React frontend
"""
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import os
from pathlib import Path

from src.auth import AuthService
from src.memory import StorageService, SearchService, NoteService
from src.transcription import TranscriptionService
from src.translation.integration import TranscriptionTranslationIntegration
from src.translation.robust_integration import RobustTranscriptionTranslationIntegration
from src.core.config import Config

app = FastAPI(title="MemoAI API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
auth_service = AuthService()
storage_service = StorageService()
search_service = SearchService()
note_service = NoteService(storage_service)
transcription_service = TranscriptionService(use_robust_pipeline=True)

# Try to initialize robust translation
try:
    translation_integration = RobustTranscriptionTranslationIntegration(
        enable_normalization=True,
        enable_llm_refinement=False
    )
except Exception:
    try:
        from src.translation.integration import TranscriptionTranslationIntegration
        translation_integration = TranscriptionTranslationIntegration()
    except Exception:
        translation_integration = None


# Dependency to get current user
def get_current_user(user_id: int = Form(...)):
    """Get current user (simplified - in production use JWT tokens)"""
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user")
    return user


# Pydantic models
class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TranslationRequest(BaseModel):
    target_language: str
    preferred_provider: Optional[str] = None
    granularity: Optional[str] = "whole_text"
    enable_paragraph_retranslation: bool = False


# Authentication endpoints
@app.post("/api/auth/register")
async def register(request: RegisterRequest):
    """Register a new user"""
    success, user_id, error = auth_service.register_user(request.username, request.password)
    if success:
        return {"success": True, "user_id": user_id, "username": request.username}
    else:
        raise HTTPException(status_code=400, detail=error)


@app.post("/api/auth/login")
async def login(request: LoginRequest):
    """Login user"""
    success, user_id, error = auth_service.login_user(request.username, request.password)
    if success:
        user_info = auth_service.get_user_by_id(user_id)
        return {"success": True, "user_id": user_id, "user": user_info}
    else:
        raise HTTPException(status_code=401, detail=error)


@app.get("/api/auth/user/{user_id}")
async def get_user(user_id: int):
    """Get user information"""
    user = auth_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    # Convert to dict if needed
    if hasattr(user, '__dict__'):
        return {
            'id': user.id,
            'username': user.username,
            'created_at': user.created_at.isoformat() if hasattr(user, 'created_at') and user.created_at else None
        }
    return user


# Transcription endpoints
@app.post("/api/transcribe/file")
async def transcribe_file(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    user_id: int = Form(...),
    enable_preprocessing: bool = Form(True),
    enable_validation: bool = Form(True),
    paragraph_format: bool = Form(False)
):
    """Transcribe uploaded audio/video file"""
    try:
        # Save uploaded file temporarily
        temp_dir = Path(Config.DATA_DIR) / "temp"
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / file.filename
        
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Transcribe
        result = transcription_service.transcribe(
            file_path=temp_file,
            language=language if language != "auto" else None,
            save_result=False,  # We'll save to database instead
            paragraph_format=paragraph_format,
            enable_preprocessing=enable_preprocessing,
            enable_validation=enable_validation
        )
        
        # Save to database
        document_id = None
        transcript_id = None
        if storage_service:
            try:
                saved_doc = storage_service.save_transcript(
                    user_id=user_id,
                    text=result.get('text', ''),
                    language=result.get('language', 'auto'),
                    source_file=str(temp_file),
                    source_type="file",
                    model_used=result.get('full_result', {}).get('model', 'unknown'),
                    paragraphs=result.get('paragraphs', []),
                    segments=result.get('segments', [])
                )
                document_id = saved_doc['document_id']
                transcript_id = saved_doc['id']
            except Exception as e:
                print(f"Warning: Failed to save to database: {e}")
        
        # Clean up temp file
        try:
            temp_file.unlink()
        except Exception:
            pass
        
        # Add database IDs to result
        result['document_id'] = document_id
        result['transcript_id'] = transcript_id
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/transcribe/url")
async def transcribe_url(
    url: str = Form(...),
    language: Optional[str] = Form(None),
    user_id: int = Form(...),
    enable_preprocessing: bool = Form(True),
    enable_validation: bool = Form(True),
    paragraph_format: bool = Form(False)
):
    """Transcribe from URL (YouTube, podcast, etc.)"""
    try:
        # Transcribe
        result = transcription_service.transcribe_url(
            url=url,
            language=language if language != "auto" else None,
            save_result=False,  # We'll save to database instead
            paragraph_format=paragraph_format,
            enable_preprocessing=enable_preprocessing,
            enable_validation=enable_validation
        )
        
        # Save to database
        document_id = None
        transcript_id = None
        if storage_service:
            try:
                saved_doc = storage_service.save_transcript(
                    user_id=user_id,
                    text=result.get('text', ''),
                    language=result.get('language', 'auto'),
                    source_url=url,
                    source_type="url",
                    model_used=result.get('full_result', {}).get('model', 'unknown'),
                    paragraphs=result.get('paragraphs', []),
                    segments=result.get('segments', [])
                )
                document_id = saved_doc['document_id']
                transcript_id = saved_doc['id']
            except Exception as e:
                print(f"Warning: Failed to save to database: {e}")
        
        # Add database IDs to result
        result['document_id'] = document_id
        result['transcript_id'] = transcript_id
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Translation endpoints
@app.post("/api/translate")
async def translate(
    transcript_id: int = Form(...),
    target_language: str = Form(...),
    user_id: int = Form(...),
    preferred_provider: Optional[str] = Form(None),
    granularity: Optional[str] = Form("whole_text"),
    enable_paragraph_retranslation: bool = Form(False)
):
    """Translate transcript"""
    try:
        # Get transcript from database
        if not storage_service:
            raise HTTPException(status_code=500, detail="Storage service not available")
        
        # Get transcript (user-isolated)
        transcripts = storage_service.get_user_transcripts(user_id=user_id, limit=1000)
        transcript = None
        for t in transcripts:
            if t.get('id') == transcript_id:
                transcript = t
                break
        
        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # Convert to transcription result format
        transcription_result = {
            'text': transcript.get('text', ''),
            'language': transcript.get('language', 'auto'),
            'paragraphs': transcript.get('paragraphs', []),
            'segments': transcript.get('segments', [])
        }
        
        # Translate
        if not translation_integration:
            raise HTTPException(status_code=500, detail="Translation service not available")
        
        # Use robust translator if available
        if isinstance(translation_integration, RobustTranscriptionTranslationIntegration):
            translation_result = translation_integration.translate_transcription(
                transcription_result=transcription_result,
                target_language=target_language,
                preferred_provider=preferred_provider,
                use_sentence_by_sentence=True,
                enable_paragraph_retranslation=enable_paragraph_retranslation
            )
        else:
            from src.translation import TranslationGranularity
            granularity_enum = TranslationGranularity.WHOLE_TEXT
            if granularity == "paragraph":
                granularity_enum = TranslationGranularity.PARAGRAPH
            elif granularity == "line_by_line":
                granularity_enum = TranslationGranularity.LINE_BY_LINE
            
            translation_result = translation_integration.translate_transcription(
                transcription_result=transcription_result,
                target_language=target_language,
                granularity=granularity_enum,
                preferred_provider=preferred_provider
            )
        
        # Save translation to database
        translated_text = translation_result.get('translated_text', '')
        if translated_text:
            try:
                # Get translated paragraphs and segments
                translated_paragraphs = None
                translated_segments = None
                translation_data = translation_result.get('translation', {})
                if translation_data:
                    translated_paragraphs = translation_data.get('paragraphs')
                    translated_segments = translation_data.get('segments')
                
                storage_service.save_translation(
                    user_id=user_id,
                    transcript_id=transcript_id,
                    translated_text=translated_text,
                    source_language=transcript['language'],
                    target_language=target_language,
                    provider=translation_result.get('provider', 'unknown'),
                    translated_paragraphs=translated_paragraphs,
                    translated_segments=translated_segments
                )
            except Exception as e:
                print(f"Warning: Failed to save translation to database: {e}")
        
        return translation_result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Storage endpoints
@app.get("/api/transcripts")
async def get_transcripts(
    user_id: int,
    limit: Optional[int] = 50,
    offset: int = 0,
    language: Optional[str] = None
):
    """Get user's transcripts"""
    if not storage_service:
        raise HTTPException(status_code=500, detail="Storage service not available")
    
    transcripts = storage_service.get_user_transcripts(
        user_id=user_id,
        limit=limit,
        offset=offset,
        language=language
    )
    
    # Add tags to each transcript
    if search_service:
        from src.memory.models import TranscriptTag, Tag
        from sqlalchemy.orm import Session
        from sqlalchemy import and_
        
        db: Session = storage_service.SessionLocal()
        try:
            for transcript in transcripts:
                transcript_id = transcript.get('id')
                if transcript_id:
                    # Get tags for this transcript
                    transcript_tags_query = db.query(Tag).join(
                        TranscriptTag, Tag.id == TranscriptTag.tag_id
                    ).filter(
                        and_(
                            TranscriptTag.transcript_id == transcript_id,
                            TranscriptTag.user_id == user_id
                        )
                    ).all()
                    
                    transcript['tags'] = [
                        {
                            'id': tag.id,
                            'name': tag.name,
                            'color': tag.color,
                            'created_at': tag.created_at.isoformat() if tag.created_at else None
                        }
                        for tag in transcript_tags_query
                    ]
                else:
                    transcript['tags'] = []
        finally:
            db.close()
    else:
        # If search service not available, add empty tags array
        for transcript in transcripts:
            transcript['tags'] = []
    
    return {"transcripts": transcripts, "count": len(transcripts)}


@app.delete("/api/transcripts/{transcript_id}")
async def delete_transcript(transcript_id: int, user_id: int):
    """Delete a transcript and all related data"""
    if not storage_service:
        raise HTTPException(status_code=500, detail="Storage service not available")
    
    # Also delete embeddings for this transcript
    try:
        from src.rag.vectorstore import FAISSVectorStore
        vectorstore = FAISSVectorStore(user_id=user_id)
        vectorstore.delete_by_transcript(transcript_id)
    except Exception as e:
        print(f"Warning: Failed to delete embeddings: {e}")
    
    success = storage_service.delete_transcript(user_id=user_id, transcript_id=transcript_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transcript not found or deletion failed")
    
    return {"success": True, "message": "Transcript deleted successfully"}


@app.get("/api/transcripts/{document_id}")
async def get_transcript(document_id: str, user_id: int):
    """Get specific transcript by document_id"""
    if not storage_service:
        raise HTTPException(status_code=500, detail="Storage service not available")
    
    transcript = storage_service.get_transcript(user_id=user_id, document_id=document_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


# Search endpoints
@app.get("/api/search/transcripts")
async def search_transcripts(
    user_id: int,
    query: str,
    language: Optional[str] = None,
    tag_names: Optional[str] = None,
    limit: int = 50
):
    """Search transcripts"""
    if not search_service:
        raise HTTPException(status_code=500, detail="Search service not available")
    
    tags = tag_names.split(",") if tag_names else None
    results = search_service.search_transcripts(
        user_id=user_id,
        query=query,
        language=language,
        tag_names=tags,
        limit=limit
    )
    return {"results": results, "count": len(results)}


# Notes endpoints
@app.post("/api/notes/generate")
async def generate_note(
    transcript_id: int = Form(...),
    user_id: int = Form(...),
    note_type: str = Form("summary"),
    target_language: Optional[str] = Form(None),  # For display only - notes are canonical
    force_regenerate: bool = Form(False)  # Allow explicit regeneration
):
    """
    Generate canonical AI note for transcript
    CANONICAL ARCHITECTURE: Notes are generated ONCE in original transcript language
    and translated for display. This ensures consistency and completeness.
    """
    try:
        if not note_service:
            raise HTTPException(status_code=500, detail="Note service not available")
        
        # Get transcript
        transcripts = storage_service.get_user_transcripts(user_id=user_id, limit=1000)
        transcript = None
        for t in transcripts:
            if t.get('id') == transcript_id:
                transcript = t
                break
        
        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # CANONICAL: Always use original transcript text and language
        # Notes are generated once in the original language, then translated for display
        transcript_text = transcript.get('text', '')
        original_language = transcript.get('language', 'auto')
        
        # Generate canonical note (in original transcript language)
        # This ensures notes are complete, consistent, and deterministic
        if note_type == "summary":
            note = note_service.generate_summary(
                user_id=user_id,
                transcript_id=transcript_id,
                transcript_text=transcript_text,
                language=original_language,  # Always use original language for canonical note
                force_regenerate=force_regenerate
            )
        elif note_type == "key_points":
            note = note_service.generate_key_points(
                user_id=user_id,
                transcript_id=transcript_id,
                transcript_text=transcript_text,
                language=original_language,  # Always use original language for canonical note
                force_regenerate=force_regenerate
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid note_type")
        
        # If target_language is specified and different from original, translate the note
        # This ensures notes are displayed in user's preferred language while maintaining canonical source
        if target_language and target_language != 'auto' and target_language != original_language:
            try:
                # Translate the canonical note content for display
                from src.translation import TranslationIntegration
                if translation_integration:
                    translated_content = translation_integration.translate_text(
                        text=note.get('content', ''),
                        source_language=original_language,
                        target_language=target_language
                    )
                    # Return note with translated content for display
                    note['translated_content'] = translated_content
                    note['display_language'] = target_language
            except Exception as e:
                print(f"Warning: Could not translate note: {e}")
                # Return canonical note even if translation fails
        
        return note
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes")
async def get_notes(user_id: int, transcript_id: Optional[int] = None):
    """Get notes for user or transcript"""
    if not storage_service:
        raise HTTPException(status_code=500, detail="Storage service not available")
    
    if transcript_id:
        notes = storage_service.get_transcript_notes(user_id=user_id, transcript_id=transcript_id)
    else:
        notes = storage_service.get_user_notes(user_id=user_id)
    
    return {"notes": notes, "count": len(notes)}


@app.delete("/api/notes/{note_id}")
async def delete_note(note_id: int, user_id: int):
    """Delete a note"""
    if not storage_service:
        raise HTTPException(status_code=500, detail="Storage service not available")
    
    success = storage_service.delete_note(user_id=user_id, note_id=note_id)
    if not success:
        raise HTTPException(status_code=404, detail="Note not found or deletion failed")
    
    return {"success": True, "message": "Note deleted successfully"}


# Tags endpoints
@app.get("/api/tags")
async def get_tags(user_id: int):
    """Get user's tags"""
    if not search_service:
        raise HTTPException(status_code=500, detail="Search service not available")
    
    tags = search_service.get_tags(user_id=user_id)
    return {"tags": tags}


@app.post("/api/tags")
async def create_tag(
    user_id: int = Form(...),
    name: str = Form(...),
    color: Optional[str] = Form(None)
):
    """Create a new tag"""
    if not search_service:
        raise HTTPException(status_code=500, detail="Search service not available")
    
    tag = search_service.create_tag(user_id=user_id, name=name, color=color)
    return tag


@app.post("/api/tags/transcript")
async def add_tag_to_transcript(
    user_id: int = Form(...),
    transcript_id: int = Form(...),
    tag_id: int = Form(...)
):
    """Add tag to transcript"""
    if not search_service:
        raise HTTPException(status_code=500, detail="Search service not available")
    
    success = search_service.add_tag_to_transcript(
        user_id=user_id,
        transcript_id=transcript_id,
        tag_id=tag_id
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add tag to transcript")
    return {"success": True}


@app.post("/api/tags/note")
async def add_tag_to_note(
    user_id: int = Form(...),
    note_id: int = Form(...),
    tag_id: int = Form(...)
):
    """Add tag to note"""
    if not search_service:
        raise HTTPException(status_code=500, detail="Search service not available")
    
    success = search_service.add_tag_to_note(
        user_id=user_id,
        note_id=note_id,
        tag_id=tag_id
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add tag to note")
    return {"success": True}


@app.delete("/api/tags/{tag_id}")
async def delete_tag(tag_id: int, user_id: int):
    """Delete a tag"""
    if not storage_service:
        raise HTTPException(status_code=500, detail="Storage service not available")
    
    success = storage_service.delete_tag(user_id=user_id, tag_id=tag_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found or deletion failed")
    
    return {"success": True, "message": "Tag deleted successfully"}


@app.delete("/api/transcripts/{transcript_id}/tags/{tag_id}")
async def remove_tag_from_transcript(transcript_id: int, tag_id: int, user_id: int):
    """Remove a tag from a transcript"""
    if not storage_service:
        raise HTTPException(status_code=500, detail="Storage service not available")
    
    success = storage_service.remove_tag_from_transcript(
        user_id=user_id,
        transcript_id=transcript_id,
        tag_id=tag_id
    )
    if not success:
        raise HTTPException(status_code=404, detail="Tag not found on transcript or removal failed")
    
    return {"success": True, "message": "Tag removed from transcript successfully"}


@app.get("/api/transcripts/{transcript_id}/tags")
async def get_transcript_tags(transcript_id: int, user_id: int):
    """Get tags for a transcript"""
    if not storage_service or not search_service:
        raise HTTPException(status_code=500, detail="Services not available")
    
    # Get transcript to verify ownership
    transcripts = storage_service.get_user_transcripts(user_id=user_id, limit=1000)
    transcript = None
    for t in transcripts:
        if t.get('id') == transcript_id:
            transcript = t
            break
    
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    
    # Get all user tags
    all_tags = search_service.get_tags(user_id=user_id)
    
    # Get transcript's tags from database
    from src.memory.models import TranscriptTag, Tag
    from sqlalchemy.orm import Session
    from sqlalchemy import and_
    
    db: Session = storage_service.SessionLocal()
    try:
        # Query TranscriptTag to get tags for this transcript
        transcript_tags_query = db.query(Tag).join(
            TranscriptTag, Tag.id == TranscriptTag.tag_id
        ).filter(
            and_(
                TranscriptTag.transcript_id == transcript_id,
                TranscriptTag.user_id == user_id
            )
        ).all()
        
        transcript_tags = [
            {
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'created_at': tag.created_at.isoformat() if tag.created_at else None
            }
            for tag in transcript_tags_query
        ]
        
        return {"tags": all_tags, "transcript_tags": transcript_tags}
    finally:
        db.close()


# Export endpoints
@app.post("/api/export/subtitles")
async def export_subtitles(
    transcript_id: int = Form(...),
    user_id: int = Form(...),
    use_translated: bool = Form(False),
    target_language: Optional[str] = Form(None),
    format: str = Form("both")  # "srt", "vtt", or "both"
):
    """Export subtitles"""
    try:
        from src.export import SubtitleGenerator
        if not SubtitleGenerator:
            raise HTTPException(status_code=500, detail="Subtitle generator not available")
        
        # Get transcript
        transcripts = storage_service.get_user_transcripts(user_id=user_id, limit=1000)
        transcript = None
        for t in transcripts:
            if t.get('id') == transcript_id:
                transcript = t
                break
        
        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # Convert to transcription data format
        transcription_data = {
            'text': transcript.get('text', ''),
            'language': transcript.get('language', 'auto'),
            'segments': transcript.get('segments', []),
            'paragraphs': transcript.get('paragraphs', []),
            'metadata': {
                'source_file': transcript.get('source_file'),
                'source_url': transcript.get('source_url')
            }
        }
        
        # ALWAYS get all translations to include both original and translated in exports
        # This ensures consistency: every export includes both languages
        all_translations = storage_service.get_translations(
            user_id=user_id,
            transcript_id=transcript_id,
            target_language=None  # Get all translations
        ) if storage_service else []
        
        # If specific language requested, use it; otherwise use first available translation
        translation = None
        if target_language:
            for t in all_translations:
                if t.get('target_language') == target_language:
                    translation = t
                    break
        
        # If no specific translation found but translations exist, use first one
        if not translation and all_translations:
            translation = all_translations[0]
        
        translated_text = translation.get('translated_text') if translation else None
        translated_segments = translation.get('translated_segments') if translation else None
        translated_paragraphs = translation.get('translated_paragraphs') if translation else None
        
        # Generate subtitles
        from src.core.config import Config
        from pathlib import Path
        
        # Prepare source file path for naming
        source_file = None
        if transcript.get('source_file'):
            source_file = Path(transcript.get('source_file'))
        elif transcript.get('source_url'):
            # Extract name from URL
            import re
            url_name = re.sub(r'[^\w\s-]', '', transcript.get('source_url', ''))
            source_file = Path(url_name[:50])  # Limit length
        
        generated_files = []
        if format == "both":
            files = SubtitleGenerator.generate_both(
                transcription_data=transcription_data,
                source_file=source_file,
                use_paragraphs=True,
                translated_text=translated_text,
                translated_segments=translated_segments
            )
            generated_files = list(files.values())
        elif format == "srt":
            file = SubtitleGenerator.generate_srt(
                transcription_data=transcription_data,
                source_file=source_file,
                use_paragraphs=True,
                translated_text=translated_text,
                translated_segments=translated_segments
            )
            generated_files = [file]
        else:  # vtt
            file = SubtitleGenerator.generate_vtt(
                transcription_data=transcription_data,
                source_file=source_file,
                use_paragraphs=True,
                translated_text=translated_text,
                translated_segments=translated_segments
            )
            generated_files = [file]
        
        # Save to database
        saved_exports = []
        for file_path in generated_files:
            file_path = Path(file_path)
            # Get relative path from exports directory
            try:
                rel_path = file_path.relative_to(Config.EXPORTS_DIR)
                rel_path_str = str(rel_path).replace('\\', '/')  # Normalize path separators
            except ValueError:
                # If file is not in exports dir, use filename only
                rel_path_str = f"subtitles/{file_path.name}"
            
            # Determine file format
            ext = file_path.suffix.lower().lstrip('.')
            file_format = ext if ext in ['srt', 'vtt'] else 'srt'
            
            # Save to database
            if storage_service:
                try:
                    file_size = file_path.stat().st_size if file_path.exists() else None
                    export_file = storage_service.save_export_file(
                        user_id=user_id,
                        file_path=rel_path_str,
                        file_type='subtitle',
                        file_format=file_format,
                        transcript_id=transcript_id,
                        language=target_language if use_translated else transcript.get('language', 'auto'),
                        is_translated=use_translated,
                        file_size=file_size
                    )
                    saved_exports.append(export_file)
                except Exception as e:
                    print(f"Warning: Failed to save export to database: {e}")
        
        if format == "both":
            return {"files": {k: str(v) for k, v in files.items()}, "saved": saved_exports}
        else:
            return {"file": str(generated_files[0]), "saved": saved_exports[0] if saved_exports else None}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/documents")
async def export_documents(
    transcript_id: int = Form(...),
    user_id: int = Form(...),
    format: str = Form("md"),  # "md", "txt", "json"
    use_translated: bool = Form(False),
    target_language: Optional[str] = Form(None)
):
    """Export transcript as document (Markdown, TXT, or JSON)"""
    try:
        from src.export import DocumentExporter
        if not DocumentExporter:
            raise HTTPException(status_code=500, detail="Document exporter not available")
        
        # Get transcript
        transcripts = storage_service.get_user_transcripts(user_id=user_id, limit=1000)
        transcript = None
        for t in transcripts:
            if t.get('id') == transcript_id:
                transcript = t
                break
        
        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # Convert to transcription data format
        transcription_data = {
            'text': transcript.get('text', ''),
            'language': transcript.get('language', 'auto'),
            'segments': transcript.get('segments', []),
            'paragraphs': transcript.get('paragraphs', []),
            'metadata': {
                'source_file': transcript.get('source_file'),
                'source_url': transcript.get('source_url')
            }
        }
        
        # ALWAYS get all translations to include both original and translated in exports
        # This ensures consistency: every document export includes both languages
        all_translations = storage_service.get_translations(
            user_id=user_id,
            transcript_id=transcript_id,
            target_language=None  # Get all translations
        ) if storage_service else []
        
        # If specific language requested, use it; otherwise use first available translation
        translation = None
        if target_language:
            for t in all_translations:
                if t.get('target_language') == target_language:
                    translation = t
                    break
        
        # If no specific translation found but translations exist, use first one
        if not translation and all_translations:
            translation = all_translations[0]
        
        translated_text = translation.get('translated_text') if translation else None
        translated_paragraphs = translation.get('translated_paragraphs') if translation else None
        
        # Generate document
        from src.core.config import Config
        from pathlib import Path
        
        source_file = None
        if transcript.get('source_file'):
            source_file = Path(transcript.get('source_file'))
        
        if format == "md":
            file_path = DocumentExporter.export_markdown(
                transcription_data=transcription_data,
                source_file=source_file,
                translated_text=translated_text,
                translated_paragraphs=translated_paragraphs
            )
        elif format == "txt":
            file_path = DocumentExporter.export_text(
                transcription_data=transcription_data,
                source_file=source_file,
                translated_text=translated_text,
                translated_paragraphs=translated_paragraphs
            )
        else:  # json
            file_path = DocumentExporter.export_json(
                transcription_data=transcription_data,
                source_file=source_file,
                translated_text=translated_text,
                translated_paragraphs=translated_paragraphs
            )
        
        file_path = Path(file_path)
        
        # Get relative path from exports directory
        try:
            rel_path = file_path.relative_to(Config.EXPORTS_DIR)
            rel_path_str = str(rel_path).replace('\\', '/')
        except ValueError:
            rel_path_str = f"documents/{file_path.name}"
        
        # Save to database
        export_file = None
        if storage_service:
            try:
                file_size = file_path.stat().st_size if file_path.exists() else None
                export_file = storage_service.save_export_file(
                    user_id=user_id,
                    file_path=rel_path_str,
                    file_type='document',
                    file_format=format,
                    transcript_id=transcript_id,
                    language=target_language if use_translated else transcript.get('language', 'auto'),
                    is_translated=use_translated,
                    file_size=file_size
                )
            except Exception as e:
                print(f"Warning: Failed to save export to database: {e}")
        
        return {"file": str(file_path), "saved": export_file}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/export/audio")
async def export_audio(
    transcript_id: int = Form(...),
    user_id: int = Form(...),
    language: str = Form("en"),
    use_translated: bool = Form(False),
    target_language: Optional[str] = Form(None),
    format: str = Form("mp3")  # "mp3" or "wav"
):
    """Export transcript as audio (TTS)"""
    try:
        from src.export import TTSSynthesizer
        if not TTSSynthesizer:
            raise HTTPException(status_code=500, detail="TTS synthesizer not available")
        
        # Get transcript
        transcripts = storage_service.get_user_transcripts(user_id=user_id, limit=1000)
        transcript = None
        for t in transcripts:
            if t.get('id') == transcript_id:
                transcript = t
                break
        
        if not transcript:
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # TTS MUST use translated text only - never original transcription
        # Generate separate audio file per translation language
        # If target_language not provided, use the most recent translation
        if not target_language:
            # Get all translations and use the most recent one
            all_translations = storage_service.get_translations(
                user_id=user_id,
                transcript_id=transcript_id,
                target_language=None  # Get all translations
            )
            if not all_translations or len(all_translations) == 0:
                raise HTTPException(
                    status_code=400, 
                    detail="No translation found. Please translate the transcript first. Audio must be generated from translated text."
                )
            # Use the most recent translation (they're ordered by created_at desc)
            target_language = all_translations[0].get('target_language')
        
        # Get translation for the specified language
        translations = storage_service.get_translations(
            user_id=user_id,
            transcript_id=transcript_id,
            target_language=target_language
        )
        
        if not translations or len(translations) == 0:
            raise HTTPException(
                status_code=404, 
                detail=f"Translation to {target_language} not found. Please translate the transcript first."
            )
        
        # Use translated text for TTS (never original)
        translation = translations[0]
        text_to_synthesize = translation.get('translated_text', '')
        synthesis_language = target_language  # Always use target language for TTS
        
        if not text_to_synthesize:
            raise HTTPException(status_code=400, detail="No translated text available for synthesis")
        
        # Generate audio with language-specific naming
        # Format: {base_name}_{transcript_id}_{language}.{format}
        from src.core.config import Config
        from pathlib import Path
        
        # Create language-specific filename
        source_file = None
        if transcript.get('source_file'):
            source_file = Path(transcript.get('source_file'))
            base_name = source_file.stem
        elif transcript.get('source_url'):
            import re
            url_name = re.sub(r'[^\w\s-]', '', transcript.get('source_url', ''))
            base_name = url_name[:50]
        else:
            base_name = f"transcript_{transcript_id}"
        
        # Include language in filename: {base_name}_{transcript_id}_{language}.{format}
        audio_filename = f"{base_name}_{transcript_id}_{target_language}.{format}"
        output_path = Config.EXPORTS_DIR / "audio" / audio_filename
        
        tts = TTSSynthesizer()
        file_path = tts.synthesize(
            text=text_to_synthesize,
            language=synthesis_language,
            output_path=output_path,  # Use language-specific path
            output_format=format
        )
        
        file_path = Path(file_path)
        
        # Get relative path from exports directory
        try:
            rel_path = file_path.relative_to(Config.EXPORTS_DIR)
            rel_path_str = str(rel_path).replace('\\', '/')
        except ValueError:
            rel_path_str = f"audio/{file_path.name}"
        
        # Save to database
        export_file = None
        if storage_service:
            try:
                file_size = file_path.stat().st_size if file_path.exists() else None
                export_file = storage_service.save_export_file(
                    user_id=user_id,
                    file_path=rel_path_str,
                    file_type='audio',
                    file_format=format,
                    transcript_id=transcript_id,
                    language=synthesis_language,
                    is_translated=use_translated,
                    file_size=file_size
                )
            except Exception as e:
                print(f"Warning: Failed to save export to database: {e}")
        
        return {"file": str(file_path), "saved": export_file}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Export file endpoints
@app.get("/api/exports")
async def list_exports(
    user_id: int,
    transcript_id: Optional[int] = None,
    file_type: Optional[str] = None  # 'subtitle', 'document', 'audio'
):
    """List export files for user (from database and filesystem)"""
    exports = []
    
    # Get exports from database
    if storage_service:
        exports = storage_service.get_user_exports(
            user_id=user_id,
            transcript_id=transcript_id,
            file_type=file_type,
            limit=100
        )
    
    # Also scan filesystem for files not in database (for backward compatibility)
    from src.core.config import Config
    export_dirs = {
        'subtitle': Config.EXPORTS_DIR / 'subtitles',  # Note: key is 'subtitle' but dir is 'subtitles'
        'document': Config.EXPORTS_DIR / 'documents',
        'audio': Config.EXPORTS_DIR / 'audio'
    }
    
    # Map file type to actual directory name for path construction
    dir_name_map = {
        'subtitle': 'subtitles',  # Use plural for actual path
        'document': 'documents',
        'audio': 'audio'
    }
    
    file_type_map = {
        'srt': ('subtitle', 'srt'),
        'vtt': ('subtitle', 'vtt'),
        'md': ('document', 'md'),
        'txt': ('document', 'txt'),
        'json': ('document', 'json'),
        'mp3': ('audio', 'mp3'),
        'wav': ('audio', 'wav')
    }
    
    # Get existing file paths from database
    existing_paths = {exp['file_path'] for exp in exports}
    
    # Scan filesystem
    for dir_type, dir_path in export_dirs.items():
        if file_type and dir_type != file_type:
            continue
        
        if dir_path.exists():
            for file_path in dir_path.iterdir():
                if file_path.is_file():
                    # Use actual directory name (plural) for path
                    actual_dir = dir_name_map.get(dir_type, dir_type)
                    rel_path = f"{actual_dir}/{file_path.name}"
                    
                    # Skip if already in database
                    if rel_path in existing_paths:
                        continue
                    
                    # Determine file format
                    ext = file_path.suffix.lower().lstrip('.')
                    if ext in file_type_map:
                        detected_type, detected_format = file_type_map[ext]
                        
                        # Add to exports list
                        try:
                            file_size = file_path.stat().st_size
                            exports.append({
                                'id': None,  # Not in database
                                'transcript_id': None,
                                'file_path': rel_path,
                                'file_type': detected_type,
                                'file_format': detected_format,
                                'language': None,
                                'is_translated': False,
                                'file_size': file_size,
                                'created_at': None
                            })
                        except Exception:
                            pass
    
    # Filter by transcript_id if specified (only for database entries)
    if transcript_id:
        exports = [exp for exp in exports if exp.get('transcript_id') == transcript_id]
    
    return {"exports": exports, "count": len(exports)}


@app.get("/api/exports/{export_id}/download")
async def download_export(export_id: int, user_id: int):
    """Download export file by ID (from database)"""
    from src.core.config import Config
    
    # Try to get from database first
    export_file = None
    if storage_service:
        exports = storage_service.get_user_exports(user_id=user_id, limit=10000)
        for exp in exports:
            if exp.get('id') == export_id:
                export_file = exp
                break
    
    if not export_file:
        raise HTTPException(status_code=404, detail="Export file not found")
    
    # Build full file path
    file_path = Config.EXPORTS_DIR / export_file['file_path']
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Determine content type
    content_type_map = {
        'srt': 'text/plain',
        'vtt': 'text/vtt',
        'md': 'text/markdown',
        'txt': 'text/plain',
        'json': 'application/json',
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav'
    }
    content_type = content_type_map.get(export_file['file_format'], 'application/octet-stream')
    
    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        filename=file_path.name
    )


@app.get("/api/exports/file/{file_path:path}/download")
async def download_export_by_path(file_path: str, user_id: int):
    """Download export file by path (for files not in database)"""
    from src.core.config import Config
    from urllib.parse import unquote
    
    # URL decode the path (FastAPI should do this, but ensure it's done)
    file_path = unquote(file_path)
    
    # Fix path: normalize 'subtitle' to 'subtitles' (plural)
    if file_path.startswith('subtitle/'):
        file_path = file_path.replace('subtitle/', 'subtitles/', 1)
    
    # Security: ensure path is within exports directory
    full_path = Config.EXPORTS_DIR / file_path
    try:
        resolved_path = full_path.resolve()
        resolved_exports_dir = Config.EXPORTS_DIR.resolve()
        resolved_path.relative_to(resolved_exports_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail=f"Invalid file path: {file_path}")
    
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(
            status_code=404, 
            detail=f"File not found: {full_path} (resolved from: {file_path})"
        )
    
    # Determine content type from extension
    ext = full_path.suffix.lower().lstrip('.')
    content_type_map = {
        'srt': 'text/plain',
        'vtt': 'text/vtt',
        'md': 'text/markdown',
        'txt': 'text/plain',
        'json': 'application/json',
        'mp3': 'audio/mpeg',
        'wav': 'audio/wav'
    }
    content_type = content_type_map.get(ext, 'application/octet-stream')
    
    return FileResponse(
        path=str(full_path),
        media_type=content_type,
        filename=full_path.name
    )


@app.get("/api/exports/{export_id}/content")
async def get_export_content(export_id: int, user_id: int):
    """Get export file content (for viewing, not downloading)"""
    from src.core.config import Config
    
    # Try to get from database first
    export_file = None
    if storage_service:
        exports = storage_service.get_user_exports(user_id=user_id, limit=10000)
        for exp in exports:
            if exp.get('id') == export_id:
                export_file = exp
                break
    
    if not export_file:
        raise HTTPException(status_code=404, detail="Export file not found")
    
    # Build full file path
    file_path = Config.EXPORTS_DIR / export_file['file_path']
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    # Read file content
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "content": content,
            "file_format": export_file['file_format'],
            "file_type": export_file['file_type'],
            "filename": file_path.name
        }
    except UnicodeDecodeError:
        # Binary file (audio) - return URL instead
        return {
            "content": None,
            "file_format": export_file['file_format'],
            "file_type": export_file['file_type'],
            "filename": file_path.name,
            "url": f"/api/exports/{export_id}/download?user_id={user_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")


@app.get("/api/exports/file/{file_path:path}/content")
async def get_export_content_by_path(file_path: str, user_id: int):
    """Get export file content by path (for viewing, not downloading)"""
    from src.core.config import Config
    from urllib.parse import unquote
    
    # URL decode the path (FastAPI should do this, but ensure it's done)
    file_path = unquote(file_path)
    
    # Fix path: normalize 'subtitle' to 'subtitles' (plural)
    if file_path.startswith('subtitle/'):
        file_path = file_path.replace('subtitle/', 'subtitles/', 1)
    
    # Security: ensure path is within exports directory
    full_path = Config.EXPORTS_DIR / file_path
    try:
        resolved_path = full_path.resolve()
        resolved_exports_dir = Config.EXPORTS_DIR.resolve()
        resolved_path.relative_to(resolved_exports_dir)
    except ValueError:
        raise HTTPException(status_code=403, detail=f"Invalid file path: {file_path}")
    
    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(
            status_code=404, 
            detail=f"File not found: {full_path} (resolved from: {file_path})"
        )
    
    # Determine file type from extension
    ext = full_path.suffix.lower().lstrip('.')
    file_type_map = {
        'srt': 'subtitle',
        'vtt': 'subtitle',
        'md': 'document',
        'txt': 'document',
        'json': 'document',
        'mp3': 'audio',
        'wav': 'audio'
    }
    file_type = file_type_map.get(ext, 'document')
    
    # Read file content (if text file)
    if file_type in ['subtitle', 'document']:
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "content": content,
                "file_format": ext,
                "file_type": file_type,
                "filename": full_path.name
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read file: {str(e)}")
    else:
        # Audio file - return URL
        return {
            "content": None,
            "file_format": ext,
            "file_type": file_type,
            "filename": full_path.name,
            "url": f"/api/exports/file/{file_path}/download?user_id={user_id}"
        }


@app.delete("/api/exports/{export_id}")
async def delete_export(export_id: int, user_id: int):
    """Delete an export file"""
    if not storage_service:
        raise HTTPException(status_code=500, detail="Storage service not available")
    
    success = storage_service.delete_export_file(user_id=user_id, export_id=export_id)
    if not success:
        raise HTTPException(status_code=404, detail="Export file not found or deletion failed")
    
    return {"success": True, "message": "Export file deleted successfully"}


@app.delete("/api/exports/file/{file_path:path}")
async def delete_export_by_path(file_path: str, user_id: int):
    """Delete an export file by path (for files not in database)"""
    from urllib.parse import unquote
    
    if not storage_service:
        raise HTTPException(status_code=500, detail="Storage service not available")
    
    # URL decode the path
    file_path = unquote(file_path)
    
    # Fix path: normalize 'subtitle' to 'subtitles' (plural) for deletion
    original_path = file_path
    if file_path.startswith('subtitle/'):
        file_path = file_path.replace('subtitle/', 'subtitles/', 1)
    
    success = storage_service.delete_export_file_by_path(user_id=user_id, file_path=file_path)
    if not success:
        # Try with original path in case it's stored differently
        if original_path != file_path:
            success = storage_service.delete_export_file_by_path(user_id=user_id, file_path=original_path)
        if not success:
            raise HTTPException(status_code=404, detail=f"File not found or deletion failed: {file_path}")
    
    return {"success": True, "message": "Export file deleted successfully"}


@app.delete("/api/rag/embeddings/{transcript_id}")
async def delete_transcript_embeddings(transcript_id: int, user_id: int):
    """Delete embeddings for a specific transcript"""
    try:
        from src.rag.vectorstore import FAISSVectorStore
        vectorstore = FAISSVectorStore(user_id=user_id)
        vectorstore.delete_by_transcript(transcript_id)
        return {"success": True, "message": f"Embeddings for transcript {transcript_id} deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete embeddings: {str(e)}")


@app.delete("/api/rag/embeddings/all")
async def delete_all_embeddings(user_id: int):
    """Delete all embeddings for the user"""
    try:
        from src.rag.vectorstore import FAISSVectorStore
        vectorstore = FAISSVectorStore(user_id=user_id)
        vectorstore.delete_all()
        return {"success": True, "message": "All embeddings deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete embeddings: {str(e)}")


# RAG endpoints
@app.post("/api/rag/index")
async def index_transcript_for_rag(
    transcript_id: int = Form(...),
    user_id: int = Form(...),
    prefer_notes: bool = Form(True),
    force_reindex: bool = Form(False)
):
    """Index a transcript for RAG retrieval (skip if already indexed unless force_reindex=True)"""
    try:
        from src.rag import RAGQAEngine
        from src.memory import StorageService
        
        storage = StorageService()
        qa_engine = RAGQAEngine(
            user_id=user_id,
            storage_service=storage,
            translation_service=translation_integration
        )
        
        # Check if already indexed
        if not force_reindex and qa_engine._is_transcript_indexed(transcript_id):
            return {
                "success": True,
                "message": f"Transcript {transcript_id} already indexed. Skipping.",
                "already_indexed": True
            }
        
        qa_engine.index_transcript(
            transcript_id=transcript_id,
            prefer_notes=prefer_notes,
            force_reindex=force_reindex
        )
        
        return {
            "success": True,
            "message": f"Transcript {transcript_id} indexed",
            "already_indexed": False
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/index-all")
async def index_all_transcripts_for_rag(
    user_id: int = Form(...),
    prefer_notes: bool = Form(True),
    force_reindex: bool = Form(False)
):
    """Index all user transcripts for RAG (skip already indexed unless force_reindex=True)"""
    try:
        from src.rag import RAGQAEngine
        from src.memory import StorageService
        
        storage = StorageService()
        qa_engine = RAGQAEngine(
            user_id=user_id,
            storage_service=storage,
            translation_service=translation_integration
        )
        
        result = qa_engine.index_all_transcripts(
            prefer_notes=prefer_notes,
            force_reindex=force_reindex
        )
        
        stats = qa_engine.vectorstore.get_stats()
        return {
            "success": True,
            "message": f"Indexing complete: {result['indexed']} indexed, {result['skipped']} skipped",
            "stats": stats,
            "indexing_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rag/query")
async def rag_query(
    question: str = Form(...),
    user_id: int = Form(...),
    top_k: int = Form(5),
    min_similarity: float = Form(0.3),
    use_advanced: bool = Form(True)
):
    """Query Advanced RAG system with a question"""
    try:
        from src.rag import RAGQAEngine
        from src.memory import StorageService
        
        storage = StorageService()
        qa_engine = RAGQAEngine(
            user_id=user_id,
            storage_service=storage,
            translation_service=translation_integration,
            enable_advanced=use_advanced
        )
        
        result = qa_engine.query(
            question=question,
            top_k=top_k,
            min_similarity=min_similarity,
            include_citations=True,
            use_advanced=use_advanced
        )
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rag/stats")
async def get_rag_stats(user_id: int):
    """Get RAG vector store statistics"""
    try:
        from src.rag import RAGQAEngine
        from src.memory import StorageService
        
        storage = StorageService()
        qa_engine = RAGQAEngine(
            user_id=user_id,
            storage_service=storage,
            translation_service=translation_integration
        )
        
        stats = qa_engine.vectorstore.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok", "version": "1.0.0"}
