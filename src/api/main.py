"""
FastAPI main application
Backend API for React frontend
"""
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
import json
import asyncio
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import os
from pathlib import Path
import aiofiles

from src.auth import AuthService
from src.memory import StorageService, SearchService, NoteService
from src.transcription import TranscriptionService
from src.translation.integration import TranscriptionTranslationIntegration
from src.translation.robust_integration import RobustTranscriptionTranslationIntegration
from src.core.config import Config

app = FastAPI(title="MemoAI API", version="1.0.0")

# Request logging middleware for debugging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests for debugging"""
    print(f"📥 Request: {request.method} {request.url.path}")
    if "/api/upload/subtitles" in request.url.path:
        print(f"🎯 Subtitle upload endpoint requested! Path: {request.url.path}")
    response = await call_next(request)
    if response.status_code == 404:
        print(f"❌ 404 for: {request.method} {request.url.path}")
    return response

# CORS middleware for React frontend - Allow all origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when allow_origins=["*"]
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Type", "Accept-Ranges"],
)

# Global exception handler to ensure CORS headers on errors
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Ensure CORS headers are included even on HTTP exceptions"""
    origin = request.headers.get('origin')
    
    headers = {}
    # Allow all origins
    if origin:
        headers['Access-Control-Allow-Origin'] = origin
    else:
        headers['Access-Control-Allow-Origin'] = '*'
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions with CORS headers"""
    origin = request.headers.get('origin')
    
    headers = {}
    # Allow all origins
    if origin:
        headers['Access-Control-Allow-Origin'] = origin
    else:
        headers['Access-Control-Allow-Origin'] = '*'
    
    import traceback
    print(f"❌ Unhandled exception: {exc}")
    print(traceback.format_exc())
    
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
        headers=headers
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


# Debug and utility endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "message": "API is running"}

@app.get("/api/routes")
async def list_routes():
    """List all available routes (for debugging)"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            routes.append({
                'path': route.path,
                'methods': list(route.methods)
            })
    return {"routes": routes}

@app.get("/api/test/subtitle-endpoint")
async def test_subtitle_endpoint():
    """Test endpoint to verify subtitle route is registered"""
    return {
        "status": "ok",
        "message": "Subtitle upload endpoint is available",
        "endpoint": "/api/upload/subtitles",
        "method": "POST"
    }

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
    """
    Transcribe uploaded audio/video file
    
    NOTE: This endpoint is for audio/video files ONLY.
    For subtitle files (.srt/.vtt), use /api/upload/subtitles instead.
    """
    try:
        # Early check: If file is a subtitle, reject and redirect to subtitle endpoint
        file_ext = Path(file.filename).suffix.lower()
        if file_ext in ['.srt', '.vtt']:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Subtitle files (.srt/.vtt) must be uploaded via /api/upload/subtitles endpoint. "
                    f"Detected subtitle file: {file.filename}"
                )
            )
        
        # Save uploaded file temporarily
        temp_dir = Path(Config.DATA_DIR) / "temp"
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / file.filename
        
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Check if file is a subtitle file (check both extension and try to parse)
        from src.transcription.subtitle_parser import SubtitleParser
        is_subtitle = False
        try:
            # First check by extension
            is_subtitle = SubtitleParser.is_subtitle_file(temp_file)
            # If extension check fails, try to parse the file to confirm
            if not is_subtitle and temp_file.exists():
                # Try to read first few lines to detect subtitle format
                try:
                    with open(temp_file, 'r', encoding='utf-8') as f:
                        first_lines = ''.join([f.readline() for _ in range(5)])
                        # Check for SRT/VTT markers
                        if 'WEBVTT' in first_lines.upper() or '-->' in first_lines:
                            is_subtitle = True
                            print(f"⚠️  Detected subtitle file by content (extension was: {temp_file.suffix})")
                except Exception:
                    pass
        except Exception as e:
            print(f"Warning: Error checking subtitle file: {e}")
        
        print(f"📄 File: {file.filename}, Extension: {temp_file.suffix}, Is Subtitle: {is_subtitle}")
        
        # Transcribe
        result = transcription_service.transcribe(
            file_path=temp_file,
            language=language if language != "auto" else None,
            save_result=False,  # We'll save to database instead
            paragraph_format=paragraph_format,
            enable_preprocessing=enable_preprocessing,
            enable_validation=enable_validation
        )
        
        # Determine language for subtitle files (they don't have language info)
        # CRITICAL: Subtitle files (.srt/.vtt) don't contain language metadata
        # Default to 'en' immediately if no language provided, or try detection as fallback
        detected_language = result.get('language')
        
        # For subtitle files, prioritize user-provided language, then detection, then default to 'en'
        if is_subtitle:
            if language and language != "auto" and language != "None" and str(language).lower() not in ('none', 'null', ''):
                detected_language = str(language).strip()
                print(f"✓ Using provided language for subtitle: {detected_language}")
            elif not detected_language or detected_language == "None" or detected_language is None:
                # Try to detect language from text (optional, can fail gracefully)
                text_to_detect = result.get('text', '')
                if text_to_detect and text_to_detect.strip():
                    try:
                        from src.rag.embeddings import MultilingualEmbedder
                        embedder = MultilingualEmbedder()
                        detected_language = embedder.detect_language(text_to_detect)
                        print(f"✓ Detected language from subtitle text: {detected_language}")
                    except Exception as e:
                        print(f"⚠️  Language detection failed: {e}, using default 'en'")
                        detected_language = 'en'  # Safe default for subtitles
                else:
                    detected_language = 'en'  # No text to detect from, use default
                    print(f"✓ No text in subtitle, using default language 'en'")
        elif not detected_language or detected_language == "None" or detected_language is None:
            # For non-subtitle files, use provided language or default
            if language and language != "auto" and language != "None" and str(language).lower() != 'none':
                detected_language = str(language).strip()
            else:
                detected_language = 'en'
        
        # Final safety check - ensure language is never None, empty, or "None"
        if not detected_language or detected_language == "None" or str(detected_language).lower() == 'none' or str(detected_language).strip() == '':
            print(f"⚠️  Language was invalid ({detected_language}), forcing to 'en'")
            detected_language = 'en'
        
        # Ensure it's a string and not None
        detected_language = str(detected_language).strip() if detected_language else 'en'
        
        print(f"✓ Determined language: {detected_language} (is_subtitle: {is_subtitle}, provided: {language})")
        
        # Update result with detected language (for subtitle files)
        if is_subtitle:
            result['language'] = detected_language
        
        # Save to database
        document_id = None
        transcript_id = None
        if storage_service:
            try:
                # Determine source_type based on file type
                source_type = "subtitle" if is_subtitle else "file"
                
                # Double-check language before saving
                final_language = str(detected_language).strip() if detected_language else 'en'
                if not final_language or final_language.lower() == 'none':
                    final_language = 'en'
                
                print(f"💾 Saving transcript with language: {final_language}, source_type: {source_type}")
                
                saved_doc = storage_service.save_transcript(
                    user_id=user_id,
                    text=result.get('text', ''),
                    language=final_language,  # Use detected/provided language, never None
                    source_file=str(temp_file),
                    source_type=source_type,
                    model_used=result.get('full_result', {}).get('model', 'unknown'),
                    paragraphs=result.get('paragraphs', []),
                    segments=result.get('segments', [])
                )
                document_id = saved_doc['document_id']
                transcript_id = saved_doc['id']
            except ValueError as e:
                # Document ID collision - storage service will retry automatically
                error_msg = str(e)
                if "Document ID" in error_msg and ("already exists" in error_msg or "collision" in error_msg):
                    print(f"⚠️  Document ID collision detected, storage service will retry automatically")
                    # Storage service now handles retry internally, but if it still fails, raise error
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to save transcript after retry: {error_msg}"
                    )
                else:
                    raise HTTPException(status_code=500, detail=f"Failed to save transcript: {error_msg}")
            except Exception as e:
                print(f"❌ Failed to save to database: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Failed to save transcript: {str(e)}")
        
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


@app.post("/api/upload/subtitles")
async def upload_subtitles(
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
    user_id: int = Form(...),
    name: Optional[str] = Form(None)
):
    """
    Dedicated endpoint for subtitle file uploads (.srt/.vtt)
    
    This endpoint is SEPARATE from audio/video transcription.
    It handles subtitle files directly without going through
    the transcription pipeline.
    
    Key differences from /api/transcribe/file:
    - No audio/video processing
    - No transcription logic
    - Language defaults to 'en' if not provided
    - Uses subtitle-specific save function
    - model_used = "subtitle_import"
    """
    print(f"🔔 upload_subtitles endpoint called! File: {file.filename if file else 'None'}")
    from src.transcription.subtitle_parser import SubtitleParser
    from src.core.config import Config
    
    try:
        # Validate file is a subtitle file
        file_ext = Path(file.filename).suffix.lower()
        if file_ext not in ['.srt', '.vtt']:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Only .srt and .vtt files are supported. Got: {file_ext}"
            )
        
        # Save uploaded file temporarily
        temp_dir = Path(Config.DATA_DIR) / "temp"
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / file.filename
        
        with open(temp_file, "wb") as f:
            content = await file.read()
            f.write(content)
        
        print(f"📄 Subtitle upload: {file.filename}, Extension: {file_ext}")
        
        # Parse subtitle file (NO transcription, just parsing)
        try:
            parsed_result = SubtitleParser.parse_subtitle(temp_file)
        except Exception as e:
            # Clean up temp file
            try:
                temp_file.unlink()
            except Exception:
                pass
            raise HTTPException(
                status_code=400,
                detail=f"Failed to parse subtitle file: {str(e)}"
            )
        
        # Extract data from parsed result
        text = parsed_result.get('text', '')
        segments = parsed_result.get('segments', [])
        
        if not text or not text.strip():
            # Clean up temp file
            try:
                temp_file.unlink()
            except Exception:
                pass
            raise HTTPException(
                status_code=400,
                detail="Subtitle file appears to be empty or contains no text"
            )
        
        # Determine language for subtitle
        # CRITICAL: Default to 'en' if not provided (subtitle files don't have language metadata)
        subtitle_language = 'en'  # Safe default
        
        if language and language.strip() and language.lower() not in ('none', 'null', 'auto', ''):
            subtitle_language = str(language).strip()
            print(f"✓ Using provided language for subtitle: {subtitle_language}")
        else:
            # Optional: Try to detect language from text (but default to 'en' if detection fails)
            try:
                from src.rag.embeddings import MultilingualEmbedder
                embedder = MultilingualEmbedder()
                detected = embedder.detect_language(text)
                if detected and detected.strip():
                    subtitle_language = detected.strip()
                    print(f"✓ Detected language from subtitle text: {subtitle_language}")
                else:
                    print(f"✓ Language detection returned empty, using default 'en'")
            except Exception as e:
                print(f"⚠️  Language detection failed: {e}, using default 'en'")
        
        # Final guarantee: language must be valid
        subtitle_language = str(subtitle_language).strip() if subtitle_language else 'en'
        if not subtitle_language:
            subtitle_language = 'en'
        
        print(f"💾 Saving subtitle with language: {subtitle_language} (guaranteed non-None)")
        
        # Save using subtitle-specific function (bypasses audio/video logic)
        document_id = None
        transcript_id = None
        if storage_service:
            try:
                saved_doc = storage_service.save_subtitle_transcript(
                    user_id=user_id,
                    text=text,
                    segments=segments,
                    source_file=str(temp_file),
                    language=subtitle_language,  # Guaranteed to be valid, never None
                    name=name
                )
                document_id = saved_doc['document_id']
                transcript_id = saved_doc['id']
                print(f"✓ Subtitle saved successfully: transcript_id={transcript_id}, document_id={document_id}")
            except Exception as e:
                print(f"❌ Failed to save subtitle: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to save subtitle: {str(e)}"
                )
        
        # Clean up temp file
        try:
            temp_file.unlink()
        except Exception:
            pass
        
        # Return result in same format as transcription endpoint for frontend compatibility
        return {
            'text': text,
            'segments': segments,
            'language': subtitle_language,
            'document_id': document_id,
            'transcript_id': transcript_id,
            'source_type': 'subtitle',
            'model_used': 'subtitle_import',
            'metadata': {
                'source_file': file.filename,
                'format': file_ext.lstrip('.'),
                'segment_count': len(segments)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in upload_subtitles: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


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
            except ValueError as e:
                # Document ID collision - storage service will retry automatically
                error_msg = str(e)
                if "Document ID" in error_msg and ("already exists" in error_msg or "collision" in error_msg):
                    print(f"⚠️  Document ID collision detected, storage service will retry automatically")
                    # Storage service now handles retry internally, but if it still fails, raise error
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to save transcript after retry: {error_msg}"
                    )
                else:
                    raise HTTPException(status_code=500, detail=f"Failed to save transcript: {error_msg}")
            except Exception as e:
                print(f"❌ Failed to save to database: {e}")
                import traceback
                traceback.print_exc()
                raise HTTPException(status_code=500, detail=f"Failed to save transcript: {str(e)}")
        
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
        
        # Check if this is a subtitle file - if so, force segment-by-segment translation
        is_subtitle = transcript.get('source_type') == 'subtitle'
        
        # Use robust translator if available
        if isinstance(translation_integration, RobustTranscriptionTranslationIntegration):
            # For subtitle files, always translate segment-by-segment to preserve timestamps
            # This is CRITICAL: Subtitle generation requires per-segment translation
            if is_subtitle:
                # Translate segments individually for subtitle files
                segments = transcription_result.get('segments', [])
                if not segments:
                    raise HTTPException(
                        status_code=400,
                        detail="Subtitle file has no segments. Cannot perform segment-level translation."
                    )
                
                print(f"📝 Translating subtitle file segment-by-segment ({len(segments)} segments)")
                translated_segments = translation_integration.translate_segments(
                    segments=segments,
                    target_language=target_language,
                    source_language=transcript['language'],
                    preferred_provider=preferred_provider
                )
                
                # Validate that translated_segments were created
                if not translated_segments or len(translated_segments) == 0:
                    raise HTTPException(
                        status_code=500,
                        detail="Segment-level translation failed. No translated segments were created."
                    )
                
                # Validate that each segment has required fields
                for i, seg in enumerate(translated_segments):
                    if 'start' not in seg or 'text' not in seg:
                        raise HTTPException(
                            status_code=500,
                            detail=f"Translated segment {i+1} is missing required fields (start, text)."
                        )
                
                # Build translation result from segments
                # NOTE: translated_text is created for database storage, but subtitle export will use translated_segments
                translated_text = ' '.join([seg.get('text', '') for seg in translated_segments])
                translation_result = {
                    'translated_text': translated_text,
                    'translation': {
                        'segments': translated_segments
                    },
                    'provider': preferred_provider or 'unknown'
                }
                print(f"✅ Translated {len(translated_segments)} subtitle segments (each with individual translation)")
            else:
                translation_result = translation_integration.translate_transcription(
                    transcription_result=transcription_result,
                    target_language=target_language,
                    preferred_provider=preferred_provider,
                    use_sentence_by_sentence=True,
                    enable_paragraph_retranslation=enable_paragraph_retranslation
                )
        else:
            from src.translation import TranslationGranularity
            # For subtitle files, use LINE_BY_LINE granularity to preserve segments
            granularity_enum = TranslationGranularity.LINE_BY_LINE if is_subtitle else TranslationGranularity.WHOLE_TEXT
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
        
        # Get original transcript text and language
        transcript_text = transcript.get('text', '')
        original_language = transcript.get('language', 'auto')
        
        # CRITICAL: If target_language is specified, generate notes in target language
        # Strategy: Translate transcript text first, then generate notes in target language
        # This ensures notes are generated directly in user's selected language
        generation_language = original_language
        text_for_generation = transcript_text
        
        if target_language and target_language != 'auto' and target_language != original_language:
            # Translate transcript text to target language first
            try:
                if translation_integration:
                    print(f"✓ Translating transcript text from {original_language} to {target_language} for note generation")
                    translated_text = translation_integration.translate_text(
                        text=transcript_text,
                        source_language=original_language,
                        target_language=target_language
                    )
                    # Accept translation even if same as original (might be legitimate)
                    if translated_text and translated_text.strip():
                        text_for_generation = translated_text
                        generation_language = target_language
                        print(f"✓ Transcript translated successfully, generating notes in {target_language}")
                    else:
                        print(f"⚠ Translation returned empty, using original text for generation")
                else:
                    print(f"⚠ Translation integration not available, using original text")
            except Exception as e:
                print(f"⚠ Failed to translate transcript for note generation: {e}")
                print(f"   Continuing with original language ({original_language}) - note will still be generated")
                # Fallback: use original text - note generation will still work
                pass
        
        # Generate note in the target language (or original if no target specified)
        try:
            if note_type == "summary":
                print(f"✓ Generating summary in {generation_language}...")
                note = note_service.generate_summary(
                    user_id=user_id,
                    transcript_id=transcript_id,
                    transcript_text=text_for_generation,
                    language=generation_language,  # Generate in target language if specified
                    force_regenerate=force_regenerate
                )
                print(f"✓ Summary generated successfully")
            elif note_type == "key_points":
                print(f"✓ Generating key points in {generation_language}...")
                note = note_service.generate_key_points(
                    user_id=user_id,
                    transcript_id=transcript_id,
                    transcript_text=text_for_generation,
                    language=generation_language,  # Generate in target language if specified
                    force_regenerate=force_regenerate
                )
                print(f"✓ Key points generated successfully")
            else:
                raise HTTPException(status_code=400, detail="Invalid note_type. Must be 'summary' or 'key_points'")
        except ValueError as e:
            # Groq API not available
            error_msg = str(e)
            if "Groq API not available" in error_msg:
                raise HTTPException(
                    status_code=500, 
                    detail="Note generation requires Groq API. Please set GROQ_API_KEY in your .env file."
                )
            raise HTTPException(status_code=500, detail=f"Failed to generate note: {error_msg}")
        except Exception as e:
            print(f"❌ Error generating {note_type}: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Failed to generate {note_type}: {str(e)}")
        
        # Note is already in target language if translation was done above
        # Set display language to match generation language
        if target_language and target_language != 'auto' and generation_language == target_language:
            note['display_language'] = target_language
            # Content is already in target language, so translated_content = content
            note['translated_content'] = note.get('content', '')
            print(f"✓ Note generated directly in target language: {target_language}")
        elif target_language and target_language != 'auto' and generation_language != target_language:
            # Fallback: If generation failed to use target language, translate the note
            print(f"⚠ Note generated in {generation_language}, translating to {target_language}")
            try:
                # Use semantic-preserving translation for structured content
                from src.translation.semantic_translator import SemanticTranslator
                from src.translation import TranslationService
                
                # Get translation service from integration
                trans_service = None
                if hasattr(translation_integration, 'translation_service'):
                    # Standard integration
                    trans_service = translation_integration.translation_service
                    print(f"✓ Using standard translation service")
                elif hasattr(translation_integration, 'robust_translator'):
                    # Robust integration - create a TranslationService wrapper
                    # The robust translator's orchestrator can be used via TranslationService
                    # For now, create a new TranslationService instance with same provider priority
                    try:
                        trans_service = TranslationService()
                        print(f"✓ Created TranslationService for robust integration")
                    except Exception as e:
                        print(f"⚠ Could not create TranslationService: {e}")
                        # If TranslationService creation fails, fall back to direct translation
                        trans_service = None
                
                if trans_service:
                    try:
                        # Use semantic translator for meaning-preserving translation
                        semantic_translator = SemanticTranslator(trans_service)
                        print(f"✓ Using semantic translator for {note_type} translation: {original_language} → {target_language}")
                        translated_content = semantic_translator.translate_structured_content(
                            content=note.get('content', ''),
                            source_language=original_language,
                            target_language=target_language,
                            content_type=note_type,  # "key_points" or "summary"
                            preferred_provider=None
                        )
                        print(f"✓ Semantic translation completed, length: {len(translated_content) if translated_content else 0}")
                    except Exception as e:
                        print(f"⚠ Semantic translator failed: {e}")
                        import traceback
                        traceback.print_exc()
                        # Fallback to direct translation
                        try:
                            if translation_integration:
                                translated_content = translation_integration.translate_text(
                                    text=note.get('content', ''),
                                    source_language=original_language,
                                    target_language=target_language
                                )
                            else:
                                translated_content = note.get('content', '')
                        except Exception as e2:
                            print(f"⚠ Fallback translation also failed: {e2}")
                            # Use original content if translation fails
                            translated_content = note.get('content', '')
                else:
                    # Fallback: use integration's translate_text method
                    try:
                        if translation_integration:
                            print(f"✓ Using integration translate_text for {note_type}: {original_language} → {target_language}")
                            translated_content = translation_integration.translate_text(
                                text=note.get('content', ''),
                                source_language=original_language,
                                target_language=target_language
                            )
                            print(f"✓ Direct translation completed, length: {len(translated_content) if translated_content else 0}")
                        else:
                            print(f"⚠ No translation integration available")
                            translated_content = note.get('content', '')
                    except Exception as e:
                        print(f"⚠ Translation failed: {e}")
                        # Use original content if translation fails
                        translated_content = note.get('content', '')
                
                    # Return note with translated content for display
                if translated_content and translated_content.strip():
                    note['translated_content'] = translated_content
                    note['display_language'] = target_language
                    print(f"✓ Successfully translated {note_type} to {target_language}")
                else:
                    print(f"⚠ Warning: Translation returned empty content for {note_type}")
                    note['translated_content'] = note.get('content', '')
                    note['display_language'] = original_language
            except Exception as e:
                print(f"⚠ Warning: Could not translate note with semantic preservation: {e}")
                import traceback
                traceback.print_exc()
                # Fallback: try simple translation
                try:
                    if translation_integration:
                        translated_content = translation_integration.translate_text(
                            text=note.get('content', ''),
                            source_language=original_language,
                            target_language=target_language
                        )
                        note['translated_content'] = translated_content
                        note['display_language'] = target_language
                except Exception as e2:
                    print(f"Warning: Fallback translation also failed: {e2}")
                # Return canonical note even if translation fails
        
        return note
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/notes")
async def get_notes(
    user_id: int, 
    transcript_id: Optional[int] = None,
    target_language: Optional[str] = None
):
    """
    Get notes for user or transcript
    If target_language is provided, translates notes for display
    """
    if not storage_service:
        raise HTTPException(status_code=500, detail="Storage service not available")
    
    if transcript_id:
        notes = storage_service.get_transcript_notes(user_id=user_id, transcript_id=transcript_id)
    else:
        notes = storage_service.get_user_notes(user_id=user_id)
    
    # If target_language is specified, translate notes for display
    if target_language and target_language != 'auto' and translation_integration:
        try:
            from src.translation.semantic_translator import SemanticTranslator
            from src.translation import TranslationService
            
            # Get translation service
            trans_service = None
            if hasattr(translation_integration, 'translation_service'):
                trans_service = translation_integration.translation_service
                print(f"✓ GET /api/notes: Using standard translation service")
            elif hasattr(translation_integration, 'robust_translator'):
                try:
                    trans_service = TranslationService()
                    print(f"✓ GET /api/notes: Created TranslationService for robust integration")
                except Exception as e:
                    print(f"⚠ GET /api/notes: Could not create TranslationService: {e}")
                    trans_service = None
            
            # Translate each note
            translated_count = 0
            for note in notes:
                original_language = note.get('language', 'auto')
                if original_language != target_language:
                    try:
                        translated_content = None
                        if trans_service:
                            # Use semantic translator
                            try:
                                semantic_translator = SemanticTranslator(trans_service)
                                translated_content = semantic_translator.translate_structured_content(
                                    content=note.get('content', ''),
                                    source_language=original_language,
                                    target_language=target_language,
                                    content_type=note.get('note_type', 'summary'),
                                    preferred_provider=None
                                )
                            except Exception as e:
                                print(f"⚠ GET /api/notes: Semantic translation failed for note {note.get('id')}: {e}")
                                # Fallback to direct translation
                                if translation_integration:
                                    translated_content = translation_integration.translate_text(
                                        text=note.get('content', ''),
                                        source_language=original_language,
                                        target_language=target_language
                                    )
                        else:
                            # Fallback to direct translation
                            if translation_integration:
                                translated_content = translation_integration.translate_text(
                                    text=note.get('content', ''),
                                    source_language=original_language,
                                    target_language=target_language
                                )
                        
                        # Accept translation even if it's the same as original (might be legitimate)
                        if translated_content and translated_content.strip():
                            note['translated_content'] = translated_content
                            note['display_language'] = target_language
                            translated_count += 1
                        else:
                            # If translation failed or returned empty, use original
                            print(f"⚠ GET /api/notes: Translation returned empty for note {note.get('id')}, using original")
                            note['translated_content'] = note.get('content', '')
                            note['display_language'] = original_language
                    except Exception as e:
                        # Silently handle translation errors - use original content
                        # Don't print warnings for every note to avoid spam
                        if translated_count == 0:  # Only print once for first error
                            print(f"⚠ GET /api/notes: Translation error (will use original content): {e}")
                        # Keep original content if translation fails
                        note['translated_content'] = note.get('content', '')
                        note['display_language'] = original_language
                else:
                    # Already in target language
                    note['translated_content'] = note.get('content', '')
                    note['display_language'] = target_language
                    translated_count += 1
            
            print(f"✓ GET /api/notes: Translated {translated_count}/{len(notes)} notes to {target_language}")
        except Exception as e:
            print(f"⚠ GET /api/notes: Translation service error: {e}")
            import traceback
            traceback.print_exc()
            # Continue without translation
    
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
        
        # Debug logging
        print(f"🔍 Export Debug: transcript_id={transcript_id}, source_type={transcript.get('source_type')}")
        print(f"   Original segments count: {len(transcription_data.get('segments', []))}")
        print(f"   Original paragraphs count: {len(transcription_data.get('paragraphs', []))}")
        
        if translated_segments:
            print(f"📝 Export: Found {len(translated_segments)} translated segments")
            if len(translated_segments) > 0:
                first_seg = translated_segments[0]
                last_seg = translated_segments[-1] if len(translated_segments) > 1 else first_seg
                print(f"   First segment: start={first_seg.get('start')}, text={first_seg.get('text', '')[:50]}...")
                print(f"   Last segment: start={last_seg.get('start')}, text={last_seg.get('text', '')[:50]}...")
                # Show a few more segments for debugging
                for i, seg in enumerate(translated_segments[:3]):
                    print(f"   Segment {i+1}: start={seg.get('start')}, text_length={len(seg.get('text', ''))}")
        else:
            print(f"⚠️  Export: No translated_segments found, will use original text only")
            if translated_text:
                print(f"   Full translated_text length: {len(translated_text)} chars")
                print(f"   First 100 chars of translated_text: {translated_text[:100]}")
        
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
        
        # Determine if this is a subtitle file - use segments, not paragraphs
        is_subtitle_file = transcript.get('source_type') == 'subtitle'
        use_paragraphs_for_export = not is_subtitle_file  # Use paragraphs only for non-subtitle files
        print(f"🔍 Export: is_subtitle_file={is_subtitle_file}, use_paragraphs={use_paragraphs_for_export}")
        
        # GUARDRAIL: For subtitle files, translated_segments is MANDATORY
        # Subtitle generation requires per-segment translation - cannot use full translated_text
        if is_subtitle_file and not translated_segments:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Subtitle files require segment-level translation. "
                    "Please translate this transcript first using /api/translate endpoint. "
                    "The translation will create translated_segments with per-segment translations."
                )
            )
        
        # For subtitle files, NEVER use translated_text - only use translated_segments
        # For non-subtitle files, we can use translated_text if segments aren't available
        export_translated_text = None if is_subtitle_file else translated_text
        
        generated_files = []
        if format == "both":
            files = SubtitleGenerator.generate_both(
                transcription_data=transcription_data,
                source_file=source_file,
                use_paragraphs=use_paragraphs_for_export,  # False for subtitle files
                translated_text=export_translated_text,  # None for subtitle files
                translated_segments=translated_segments
            )
            generated_files = list(files.values())
        elif format == "srt":
            file = SubtitleGenerator.generate_srt(
                transcription_data=transcription_data,
                source_file=source_file,
                use_paragraphs=use_paragraphs_for_export,  # False for subtitle files
                translated_text=export_translated_text,  # None for subtitle files
                translated_segments=translated_segments
            )
            generated_files = [file]
        else:  # vtt
            file = SubtitleGenerator.generate_vtt(
                transcription_data=transcription_data,
                source_file=source_file,
                use_paragraphs=use_paragraphs_for_export,  # False for subtitle files
                translated_text=export_translated_text,  # None for subtitle files
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

def _normalize_export_path(relative_path: str) -> Path:
    """
    Normalize a relative export file path to a safe, absolute Path.
    
    Handles:
    - Forward/backward slashes (Windows compatibility)
    - Leading slashes
    - Duplicated 'exports/' prefix
    - Path traversal attempts
    
    Args:
        relative_path: Relative path from exports directory (e.g., "audio/file.mp3")
    
    Returns:
        Normalized Path object within EXPORTS_DIR
    
    Raises:
        ValueError: If path is invalid or attempts traversal
    """
    from src.core.config import Config
    
    # Remove leading slashes and normalize separators
    normalized = relative_path.lstrip('/\\').replace('\\', '/')
    
    # Remove duplicated 'exports/' prefix if present
    if normalized.startswith('exports/'):
        normalized = normalized[8:]  # Remove 'exports/'
    
    # Remove any remaining leading slashes
    normalized = normalized.lstrip('/')
    
    # Security: Check for path traversal attempts
    if '..' in normalized or normalized.startswith('/'):
        raise ValueError(f"Invalid path: contains traversal or absolute path")
    
    # Build full path
    full_path = Config.EXPORTS_DIR / normalized
    
    # Resolve to absolute path and verify it's within EXPORTS_DIR
    try:
        resolved_path = full_path.resolve()
        resolved_exports_dir = Config.EXPORTS_DIR.resolve()
        
        # Ensure the resolved path is within exports directory
        resolved_path.relative_to(resolved_exports_dir)
        
        return resolved_path
    except (ValueError, OSError) as e:
        raise ValueError(f"Path traversal detected or invalid path: {relative_path}")


def _get_file_response(file_path: Path, content_type: str, filename: str, force_download: bool = False, request_origin: Optional[str] = None):
    """
    Create a FileResponse for file download/playback.
    FileResponse is simpler and has better CORS support than StreamingResponse.
    
    Args:
        file_path: Absolute path to the file
        content_type: MIME type
        filename: Filename for Content-Disposition header
        force_download: If True, force download; if False, allow inline playback
        request_origin: Origin header from request (for CORS)
    
    Returns:
        FileResponse with proper headers including CORS
    """
    # Verify file exists and is readable
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
    
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Path is not a file: {file_path}")
    
    try:
        # Verify we can read the file
        file_path.stat()
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Cannot read file: {str(e)}")
    
    # Determine Content-Disposition
    if force_download:
        disposition = f'attachment; filename="{filename}"'
    else:
        # For audio files, use 'inline' to allow playback
        if content_type.startswith('audio/'):
            disposition = f'inline; filename="{filename}"'
        else:
            disposition = f'attachment; filename="{filename}"'
    
    # Build headers with explicit CORS support
    headers = {
        'Content-Disposition': disposition,
        'Accept-Ranges': 'bytes',
        'Cache-Control': 'public, max-age=3600',
    }
    
    # Add explicit CORS headers (allow all origins)
    if request_origin:
        headers['Access-Control-Allow-Origin'] = request_origin
    else:
        headers['Access-Control-Allow-Origin'] = '*'
    headers['Access-Control-Allow-Methods'] = 'GET, OPTIONS'
    headers['Access-Control-Allow-Headers'] = '*'
    headers['Access-Control-Expose-Headers'] = 'Content-Disposition, Content-Length, Content-Type, Accept-Ranges'
    
    # Use FileResponse with explicit CORS headers
    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        filename=filename,
        headers=headers
    )


@app.options("/api/exports/{export_id}/download")
async def download_export_options(export_id: int, request: Request):
    """Handle CORS preflight for download endpoint"""
    origin = request.headers.get('origin')
    
    headers = {
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Max-Age': '3600',
    }
    
    # Allow all origins
    if origin:
        headers['Access-Control-Allow-Origin'] = origin
    else:
        headers['Access-Control-Allow-Origin'] = '*'
    
    return JSONResponse(content={}, headers=headers)


@app.get("/api/exports/{export_id}/download")
async def download_export(
    export_id: int, 
    user_id: int,
    request: Request,
    force_download: bool = False
):
    """
    Download export file by ID (from database).
    
    Args:
        export_id: Export file ID from database
        user_id: User ID for authorization
        request: FastAPI Request object (for CORS origin)
        force_download: If True, force download; if False, allow inline playback for audio
    """
    from src.core.config import Config
    import traceback
    
    try:
        # Get origin from request headers for CORS
        origin = request.headers.get('origin')
        
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
    
        # Normalize and resolve file path
        try:
            stored_path = export_file['file_path']
            print(f"🔍 DEBUG: Stored path from DB: '{stored_path}'")
            print(f"🔍 DEBUG: EXPORTS_DIR: {Config.EXPORTS_DIR}")
            file_path = _normalize_export_path(stored_path)
            print(f"🔍 DEBUG: Normalized path: {file_path}")
            print(f"🔍 DEBUG: Path exists: {file_path.exists()}, is_file: {file_path.is_file() if file_path.exists() else 'N/A'}")
        except ValueError as e:
            print(f"❌ Path normalization error: {e}")
            print(f"❌ Stored path was: '{stored_path}'")
            raise HTTPException(status_code=400, detail=f"Invalid file path: {str(e)}")
        
        # Verify file exists
        if not file_path.exists() or not file_path.is_file():
            # Try alternative locations (for backward compatibility)
            alt_paths = [
                Config.EXPORTS_DIR / stored_path,
                Config.EXPORTS_DIR / "audio" / Path(stored_path).name,
                Config.EXPORTS_DIR / "subtitles" / Path(stored_path).name,
                Config.EXPORTS_DIR / "documents" / Path(stored_path).name,
            ]
            
            file_path = None
            for alt_path in alt_paths:
                try:
                    resolved = alt_path.resolve()
                    if resolved.exists() and resolved.is_file():
                        # Verify it's still within EXPORTS_DIR
                        resolved.relative_to(Config.EXPORTS_DIR.resolve())
                        file_path = resolved
                        print(f"✓ Found file at alternative path: {file_path}")
                        break
                except (ValueError, OSError) as e:
                    continue
            
            if not file_path:
                print(f"❌ File not found. Stored path: {stored_path}, EXPORTS_DIR: {Config.EXPORTS_DIR}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"File not found on disk. Stored path: {stored_path}"
                )
        
        print(f"✓ Serving file: {file_path}")
        
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
        content_type = content_type_map.get(export_file.get('file_format', '').lower(), 'application/octet-stream')
        
        # Use file extension as fallback if format not in map
        if content_type == 'application/octet-stream':
            ext = file_path.suffix.lower().lstrip('.')
            content_type = content_type_map.get(ext, 'application/octet-stream')
        
        return _get_file_response(
            file_path=file_path,
            content_type=content_type,
            filename=file_path.name,
            force_download=force_download,
            request_origin=origin
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in download_export: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
        )


@app.options("/api/exports/file/{file_path:path}/download")
async def download_export_by_path_options(file_path: str, request: Request):
    """Handle CORS preflight for path-based download endpoint"""
    origin = request.headers.get('origin')
    
    headers = {
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Max-Age': '3600',
    }
    
    # Allow all origins
    if origin:
        headers['Access-Control-Allow-Origin'] = origin
    else:
        headers['Access-Control-Allow-Origin'] = '*'
    
    return JSONResponse(content={}, headers=headers)


@app.options("/api/download/file/{file_type}/{filename}")
async def download_file_direct_options(file_type: str, filename: str, request: Request):
    """Handle CORS preflight for direct file download endpoint"""
    origin = request.headers.get('origin')
    
    headers = {
        'Access-Control-Allow-Methods': 'GET, OPTIONS',
        'Access-Control-Allow-Headers': '*',
        'Access-Control-Max-Age': '3600',
    }
    
    # Allow all origins
    if origin:
        headers['Access-Control-Allow-Origin'] = origin
    else:
        headers['Access-Control-Allow-Origin'] = '*'
    
    return JSONResponse(content={}, headers=headers)


@app.get("/api/download/file/{file_type}/{filename}")
async def download_file_direct(
    file_type: str,  # 'audio', 'documents', or 'subtitles'
    filename: str,
    request: Request,
    force_download: bool = False
):
    """
    Simple direct file download from exports directories.
    Downloads files from: audio/, documents/, or subtitles/ directories.
    
    Args:
        file_type: One of 'audio', 'documents', or 'subtitles'
        filename: Name of the file to download
        request: FastAPI Request object (for CORS)
        force_download: If True, force download; if False, allow inline playback for audio
    
    Example:
        GET /api/download/file/audio/myfile.mp3
        GET /api/download/file/documents/myfile.md
        GET /api/download/file/subtitles/myfile.srt
    """
    from src.core.config import Config
    from urllib.parse import unquote
    import traceback
    
    try:
        # Get origin for CORS
        origin = request.headers.get('origin')
        
        # URL decode filename
        filename = unquote(filename)
        
        # Validate file_type
        allowed_types = ['audio', 'documents', 'subtitles']
        if file_type not in allowed_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid file_type. Must be one of: {', '.join(allowed_types)}"
            )
        
        # Build file path
        file_path = Config.EXPORTS_DIR / file_type / filename
        
        # Security: Verify file is within exports directory
        try:
            resolved_path = file_path.resolve()
            resolved_exports_dir = Config.EXPORTS_DIR.resolve()
            resolved_path.relative_to(resolved_exports_dir)
        except (ValueError, OSError):
            raise HTTPException(status_code=403, detail="Invalid file path")
        
        # Verify file exists
        if not file_path.exists() or not file_path.is_file():
            raise HTTPException(
                status_code=404, 
                detail=f"File not found: {filename} in {file_type}/ directory"
            )
        
        print(f"✓ Serving file: {file_path}")
        
        # Determine content type from extension
        ext = file_path.suffix.lower().lstrip('.')
        content_type_map = {
            'srt': 'text/plain',
            'vtt': 'text/vtt',
            'md': 'text/markdown',
            'txt': 'text/plain',
            'json': 'application/json',
            'mp3': 'audio/mpeg',
            'wav': 'audio/wav',
            'm4a': 'audio/mp4',
            'ogg': 'audio/ogg'
        }
        content_type = content_type_map.get(ext, 'application/octet-stream')
        
        # Use the existing _get_file_response function
        return _get_file_response(
            file_path=file_path,
            content_type=content_type,
            filename=filename,
            force_download=force_download,
            request_origin=origin
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in download_file_direct: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
    )


@app.get("/api/exports/file/{file_path:path}/download")
async def download_export_by_path(
    file_path: str, 
    user_id: int,
    request: Request,
    force_download: bool = False
):
    """
    Download export file by path (for files not in database).
    
    Args:
        file_path: Relative path from exports directory (e.g., "audio/file.mp3")
        user_id: User ID for authorization
        request: FastAPI Request object (for CORS origin)
        force_download: If True, force download; if False, allow inline playback for audio
    """
    from src.core.config import Config
    from urllib.parse import unquote
    import traceback
    
    try:
        # Get origin from request headers for CORS
        origin = request.headers.get('origin')
        
        # URL decode the path (FastAPI should do this, but ensure it's done)
        file_path = unquote(file_path)
        
        # Fix path: normalize 'subtitle' to 'subtitles' (plural)
        if file_path.startswith('subtitle/'):
            file_path = file_path.replace('subtitle/', 'subtitles/', 1)
        
        # Normalize and resolve file path (with security checks)
        try:
            resolved_path = _normalize_export_path(file_path)
        except ValueError as e:
            print(f"❌ Path normalization error: {e}")
            raise HTTPException(status_code=403, detail=f"Invalid file path: {str(e)}")
        
        # Verify file exists
        if not resolved_path.exists() or not resolved_path.is_file():
            # Try alternative locations (for backward compatibility)
            alt_paths = [
                Config.EXPORTS_DIR / file_path,
                Config.EXPORTS_DIR / "audio" / Path(file_path).name,
                Config.EXPORTS_DIR / "subtitles" / Path(file_path).name,
                Config.EXPORTS_DIR / "documents" / Path(file_path).name,
            ]
            
            found_path = None
            for alt_path in alt_paths:
                try:
                    resolved = alt_path.resolve()
                    if resolved.exists() and resolved.is_file():
                        # Verify it's still within EXPORTS_DIR
                        resolved.relative_to(Config.EXPORTS_DIR.resolve())
                        found_path = resolved
                        print(f"✓ Found file at alternative path: {found_path}")
                        break
                except (ValueError, OSError):
                    continue
            
            if not found_path:
                print(f"❌ File not found. Path: {file_path}, EXPORTS_DIR: {Config.EXPORTS_DIR}")
                raise HTTPException(
                    status_code=404, 
                    detail=f"File not found: {resolved_path} (resolved from: {file_path})"
                )
            else:
                resolved_path = found_path
        
        print(f"✓ Serving file: {resolved_path}")
        
        # Determine content type from extension
        ext = resolved_path.suffix.lower().lstrip('.')
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
        
        return _get_file_response(
            file_path=resolved_path,
            content_type=content_type,
            filename=resolved_path.name,
            force_download=force_download,
            request_origin=origin
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error in download_export_by_path: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f"Internal server error: {str(e)}"
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
async def delete_transcript_embeddings(transcript_id: int, user_id: int = Query(...)):
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
        # Ensure user_id is valid
        if user_id < 1:
            raise HTTPException(status_code=422, detail="Invalid user_id: must be >= 1")
        
        from src.rag.vectorstore import FAISSVectorStore
        vectorstore = FAISSVectorStore(user_id=user_id)
        
        # Get stats before deletion for logging
        stats_before = vectorstore.get_stats()
        num_vectors = stats_before.get('num_vectors', 0)
        
        # Delete all embeddings
        vectorstore.delete_all()
        
        # Verify deletion
        stats_after = vectorstore.get_stats()
        num_vectors_after = stats_after.get('num_vectors', 0)
        
        if num_vectors_after > 0:
            raise HTTPException(
                status_code=500, 
                detail=f"Deletion incomplete: {num_vectors_after} vectors still remain"
            )
        
        return {
            "success": True, 
            "message": f"All embeddings deleted successfully ({num_vectors} vectors removed)",
            "vectors_deleted": num_vectors
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid user_id: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"❌ Error deleting embeddings: {e}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete embeddings: {str(e)}"
        )


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
    top_k: int = Form(10),  # Increased default for better fact coverage
    min_similarity: float = Form(0.2),  # Lower default for better multilingual support
    use_advanced: bool = Form(True),
    conversation_id: Optional[int] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """Query Advanced RAG system with a question (supports conversation context)"""
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
            use_advanced=use_advanced,
            conversation_id=conversation_id,
            session_id=session_id
        )
        
        return result
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ RAG Query Error: {e}")
        print(f"Full traceback:\n{error_trace}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@app.post("/api/rag/query/stream")
async def rag_query_stream(
    question: str = Form(...),
    user_id: int = Form(...),
    top_k: int = Form(10),
    min_similarity: float = Form(0.2),
    use_advanced: bool = Form(True),
    conversation_id: Optional[int] = Form(None),
    session_id: Optional[str] = Form(None)
):
    """Stream RAG query response using Server-Sent Events (supports conversation context)"""
    async def generate_stream():
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
            
            # Handle conversation context
            conversation_history = []
            current_conversation_id = conversation_id
            current_session_id = session_id
            
            if session_id or conversation_id:
                if session_id and not conversation_id:
                    conv = storage.get_conversation(user_id=user_id, session_id=session_id)
                    if conv:
                        current_conversation_id = conv['conversation_id']
                    else:
                        query_lang = qa_engine.detect_query_language(question)
                        new_conv = storage.create_conversation(
                            user_id=user_id,
                            session_id=session_id,
                            language=query_lang
                        )
                        current_conversation_id = new_conv['conversation_id']
                        current_session_id = new_conv['session_id']
                
                if current_conversation_id:
                    conv = storage.get_conversation(user_id=user_id, conversation_id=current_conversation_id)
                    if conv and conv.get('messages'):
                        conversation_history = conv['messages'][-10:]
            
            # Detect language
            query_lang = qa_engine.detect_query_language(question)
            
            # Send initial metadata
            yield f"data: {json.dumps({'type': 'metadata', 'language': query_lang})}\n\n"
            
            # Perform search (non-streaming part)
            query_embedding = qa_engine.embedder.embed_text(question)
            results = qa_engine.vectorstore.search(
                query_embedding=query_embedding,
                k=top_k * 3
            )
            
            # Filter results by similarity
            base_threshold = min_similarity
            multilingual_threshold = base_threshold * 0.7
            filtered_results = [
                (meta, score) for meta, score in results
                if score >= multilingual_threshold
            ]
            
            if not filtered_results and results:
                filtered_results = results[:top_k]
            
            if not filtered_results:
                # No results - send general knowledge answer
                yield f"data: {json.dumps({'type': 'answer_chunk', 'content': 'No relevant information found in your stored transcripts.'})}\n\n"
                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                return
            
            retrieved_chunks = [meta for meta, _ in filtered_results[:15]]
            
            # Stream answer using LLM
            if use_advanced and qa_engine.refiner and qa_engine.refiner.use_llm:
                # Stream from refiner
                full_answer = ""
                for chunk in qa_engine.refiner._refine_with_llm_streaming(
                    question=question,
                    retrieved_chunks=retrieved_chunks,
                    language=query_lang,
                    max_length=500,
                    conversation_history=conversation_history
                ):
                    full_answer += chunk
                    yield f"data: {json.dumps({'type': 'answer_chunk', 'content': chunk})}\n\n"
            else:
                # Fallback: simple concatenation
                answer_parts = []
                for meta in retrieved_chunks[:3]:
                    text = meta.get('text', '')
                    if text:
                        answer_parts.append(text)
                full_answer = ' '.join(answer_parts)
                # Stream word by word for effect
                words = full_answer.split()
                for word in words:
                    yield f"data: {json.dumps({'type': 'answer_chunk', 'content': word + ' '})}\n\n"
                    await asyncio.sleep(0.01)  # Small delay for streaming effect
            
            # Save to conversation if using conversation context
            if current_conversation_id and full_answer:
                try:
                    storage.add_message(
                        user_id=user_id,
                        conversation_id=current_conversation_id,
                        role='user',
                        content=question,
                        metadata={'language': query_lang}
                    )
                    storage.add_message(
                        user_id=user_id,
                        conversation_id=current_conversation_id,
                        role='assistant',
                        content=full_answer,
                        metadata={'language': query_lang, 'num_chunks': len(retrieved_chunks)}
                    )
                except Exception as e:
                    print(f"⚠️  Failed to save conversation message: {e}")
            
            # Send citations
            citations = []
            for i, (meta, score) in enumerate(filtered_results[:top_k]):
                citations.append({
                    'chunk_index': i + 1,
                    'document_id': meta.get('document_id'),
                    'transcript_id': meta.get('transcript_id'),
                    'similarity': float(score)
                })
            
            yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'conversation_id': current_conversation_id, 'session_id': current_session_id})}\n\n"
            
        except Exception as e:
            print(f"❌ Streaming error: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ==================== Conversation Management Endpoints ====================

@app.post("/api/conversations/create")
async def create_conversation(
    user_id: int = Form(...),
    session_id: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    language: Optional[str] = Form(None)
):
    """Create a new conversation session"""
    try:
        from src.memory import StorageService
        
        storage = StorageService()
        conversation = storage.create_conversation(
            user_id=user_id,
            session_id=session_id,
            title=title,
            language=language
        )
        
        return conversation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations")
async def list_conversations(
    user_id: int,
    limit: int = 50
):
    """Get all conversations for a user"""
    try:
        from src.memory import StorageService
        
        storage = StorageService()
        conversations = storage.get_user_conversations(
            user_id=user_id,
            limit=limit
        )
        
        return {
            'conversations': conversations,
            'count': len(conversations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    user_id: int,
    limit_messages: int = 100
):
    """Get a specific conversation with messages (limited for performance)"""
    try:
        from src.memory import StorageService
        
        storage = StorageService()
        conversation = storage.get_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            limit_messages=limit_messages
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/conversations/session/{session_id}")
async def get_conversation_by_session(
    session_id: str,
    user_id: int,
    limit_messages: int = 100
):
    """Get a conversation by session ID (limited for performance)"""
    try:
        from src.memory import StorageService
        
        storage = StorageService()
        conversation = storage.get_conversation(
            user_id=user_id,
            session_id=session_id,
            limit_messages=limit_messages
        )
        
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    user_id: int
):
    """Delete a conversation and all its messages"""
    try:
        from src.memory import StorageService
        
        storage = StorageService()
        deleted = storage.delete_conversation(
            user_id=user_id,
            conversation_id=conversation_id
        )
        
        if not deleted:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        return {'success': True, 'message': 'Conversation deleted'}
    except HTTPException:
        raise
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


# Verify endpoints on startup
@app.on_event("startup")
async def verify_endpoints():
    """Verify critical endpoints are registered when server starts"""
    registered_paths = [route.path for route in app.routes if hasattr(route, 'path')]
    required_endpoints = [
        "/api/health",
        "/api/routes", 
        "/api/test/subtitle-endpoint",
        "/api/upload/subtitles"
    ]
    missing = [ep for ep in required_endpoints if ep not in registered_paths]
    if missing:
        print(f"⚠️  WARNING: Some endpoints not registered: {missing}")
    else:
        print(f"✅ All endpoints registered successfully: {required_endpoints}")
    
    # Also print all POST routes for debugging
    post_routes = [route.path for route in app.routes if hasattr(route, 'methods') and 'POST' in route.methods]
    print(f"📋 All POST routes: {sorted(post_routes)}")


