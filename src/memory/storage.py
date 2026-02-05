"""
Persistent storage service for transcripts, translations, and notes
Ensures user isolation and immutable document storage
"""
import secrets
from typing import Optional, Dict, List, Any
from datetime import datetime
from sqlalchemy import create_engine, and_, func
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError

from src.memory.models import (
    Transcript, Translation, Note, Tag, TranscriptTag, NoteTag, ExportFile,
    Conversation, ConversationMessage
)
from src.core.config import Config
from src.core.config import Config


class StorageService:
    """
    Persistent storage service with user isolation
    Ensures immutable documents (no overwrites)
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize storage service
        
        Args:
            database_url: Database URL (defaults to Config.DATABASE_URL)
        """
        self.database_url = database_url or Config.DATABASE_URL
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        from src.core.database import Base
        Base.metadata.create_all(self.engine)
    
    def _generate_document_id(self) -> str:
        """Generate unique document ID"""
        return secrets.token_urlsafe(32)
    
    def save_transcript(
        self,
        user_id: int,
        text: str,
        language: str,
        source_file: Optional[str] = None,
        source_url: Optional[str] = None,
        source_type: str = "file",
        model_used: Optional[str] = None,
        paragraphs: Optional[List[Dict]] = None,
        segments: Optional[List[Dict]] = None,
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save transcript as immutable document
        
        Args:
            user_id: User ID (for isolation)
            text: Transcript text
            language: Language code
            source_file: Source file path (if file)
            source_url: Source URL (if URL)
            source_type: Type of source ('file', 'url', 'subtitle')
            model_used: Whisper model used
            paragraphs: Paragraph-level data
            segments: Segment-level data
            document_id: Optional document ID (generates new if None)
            
        Returns:
            Dictionary with document_id and transcript data
        """
        # CRITICAL: Language validation MUST happen BEFORE any database operation
        # This ensures language is NEVER None when creating Transcript object
        # For subtitle files (source_type='subtitle'), default to 'en' if not provided
        
        # Step 1: Convert to string and handle None
        if language is None:
            language = None
        else:
            language = str(language).strip()
        
        # Step 2: Validate and set default if invalid
        if not language or language == '' or language.lower() in ('none', 'auto', 'null'):
            # For subtitle files, default to 'en' immediately (no detection needed)
            if source_type == 'subtitle':
                language = 'en'
                print(f"✓ Subtitle file: using default language 'en' (no language metadata in subtitle files)")
            else:
                # For other files, try to detect from text
                try:
                    from src.rag.embeddings import MultilingualEmbedder
                    embedder = MultilingualEmbedder()
                    if text and text.strip():
                        language = embedder.detect_language(text)
                        print(f"✓ Auto-detected language in save_transcript: {language}")
                    else:
                        language = 'en'
                except Exception as e:
                    print(f"⚠️  Language detection failed in save_transcript: {e}, using 'en'")
                    language = 'en'  # Safe default
        
        # Step 3: Final guarantee - language MUST be a non-empty string
        language = str(language).strip() if language else 'en'
        if not language or language.lower() in ('none', 'null', ''):
            language = 'en'
        
        # Step 4: Assert language is valid (defensive check)
        assert language and language.strip() != '', f"Language validation failed: language={repr(language)}"
        
        print(f"💾 save_transcript: language={language}, source_type={source_type}, text_length={len(text) if text else 0}")
        
        db: Session = self.SessionLocal()
        try:
            # Generate unique document ID if not provided
            if not document_id:
                document_id = self._generate_document_id()
                # Ensure uniqueness (retry up to 10 times)
                max_retries = 10
                retry_count = 0
                while db.query(Transcript).filter(Transcript.document_id == document_id).first():
                    retry_count += 1
                    if retry_count >= max_retries:
                        raise ValueError("Failed to generate unique document ID after multiple attempts")
                    document_id = self._generate_document_id()
            
            # For subtitle files, check if we should allow duplicates or skip
            # (Subtitle files can be re-uploaded for translation, so allow duplicates)
            # But ensure document_id is always unique
            
            # Create new transcript (never overwrite existing)
            transcript = Transcript(
                document_id=document_id,
                user_id=user_id,
                source_file=source_file,
                source_url=source_url,
                source_type=source_type,
                text=text,
                language=language,
                model_used=model_used,
                paragraphs=paragraphs or [],
                segments=segments or []
            )
            
            db.add(transcript)
            db.commit()
            db.refresh(transcript)
            
            return {
                'document_id': transcript.document_id,
                'id': transcript.id,
                'user_id': transcript.user_id,
                'created_at': transcript.created_at.isoformat() if transcript.created_at else None
            }
            
        except IntegrityError as e:
            db.rollback()
            error_str = str(e).lower()
            
            # CRITICAL: Separate NOT NULL constraint errors from document_id collisions
            # NOT NULL errors indicate a validation problem (language=None) - don't retry, raise immediately
            if 'not null' in error_str and 'language' in error_str:
                # This should NEVER happen if validation above worked correctly
                # But if it does, it means language validation failed - raise clear error
                print(f"❌ CRITICAL: Language validation failed! language={language}, text_length={len(text) if text else 0}")
                raise ValueError(
                    f"Language cannot be NULL. Validation failed. "
                    f"This indicates a bug in language validation logic. "
                    f"Language value was: {repr(language)}"
                )
            
            # Only retry for actual document_id collisions (unique constraint violations)
            if 'document_id' in error_str or ('unique' in error_str and 'document_id' in error_str):
                try:
                    # Generate new document_id and retry
                    new_document_id = self._generate_document_id()
                    max_retries = 10
                    retry_count = 0
                    while db.query(Transcript).filter(Transcript.document_id == new_document_id).first():
                        retry_count += 1
                        if retry_count >= max_retries:
                            raise ValueError("Failed to generate unique document ID after multiple attempts")
                        new_document_id = self._generate_document_id()
                    
                    # Use the already-validated language (should never be None at this point)
                    retry_language = language
                    
                    # Final safety check (should not be needed, but defensive programming)
                    if not retry_language or str(retry_language).strip() == '' or str(retry_language).lower() == 'none':
                        retry_language = 'en'
                    retry_language = str(retry_language).strip()
                    
                    print(f"🔄 Retry (document_id collision): language={retry_language}, source_type={source_type}, document_id={new_document_id}")
                    
                    # Retry with new document_id
                    transcript = Transcript(
                        document_id=new_document_id,
                        user_id=user_id,
                        source_file=source_file,
                        source_url=source_url,
                        source_type=source_type,
                        text=text,
                        language=retry_language,  # Guaranteed to be valid
                        model_used=model_used,
                        paragraphs=paragraphs or [],
                        segments=segments or []
                    )
                    
                    db.add(transcript)
                    db.commit()
                    db.refresh(transcript)
                    
                    return {
                        'document_id': transcript.document_id,
                        'id': transcript.id,
                        'user_id': transcript.user_id,
                        'created_at': transcript.created_at.isoformat() if transcript.created_at else None
                    }
                except Exception as retry_error:
                    print(f"❌ Retry failed: {retry_error}")
                    import traceback
                    traceback.print_exc()
                    raise ValueError(f"Document ID collision and retry failed: {str(retry_error)}")
            else:
                # Other integrity errors (foreign key, etc.) - don't retry
                raise ValueError(f"Database integrity error: {str(e)}")
        except Exception as e:
            db.rollback()
            print(f"❌ save_transcript error: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to save transcript: {str(e)}")
        finally:
            db.close()
    
    def save_translation(
        self,
        user_id: int,
        transcript_id: int,
        translated_text: str,
        source_language: str,
        target_language: str,
        provider: Optional[str] = None,
        translated_paragraphs: Optional[List[Dict]] = None,
        translated_segments: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Save translation linked to transcript
        
        Args:
            user_id: User ID (for isolation)
            transcript_id: Transcript ID
            translated_text: Translated text
            source_language: Source language code
            target_language: Target language code
            provider: Translation provider used
            translated_paragraphs: Translated paragraphs
            translated_segments: Translated segments
            
        Returns:
            Dictionary with translation data
        """
        db: Session = self.SessionLocal()
        try:
            # Verify transcript belongs to user
            transcript = db.query(Transcript).filter(
                and_(Transcript.id == transcript_id, Transcript.user_id == user_id)
            ).first()
            
            if not transcript:
                raise ValueError("Transcript not found or access denied")
            
            # Check if translation already exists for this language
            existing = db.query(Translation).filter(
                and_(
                    Translation.transcript_id == transcript_id,
                    Translation.target_language == target_language,
                    Translation.user_id == user_id
                )
            ).first()
            
            if existing:
                # Update existing translation (allow updates for same language)
                existing.translated_text = translated_text
                existing.translated_paragraphs = translated_paragraphs or []
                existing.translated_segments = translated_segments or []
                existing.provider = provider
                translation = existing
            else:
                # Create new translation
                translation = Translation(
                    transcript_id=transcript_id,
                    user_id=user_id,
                    source_language=source_language,
                    target_language=target_language,
                    translated_text=translated_text,
                    translated_paragraphs=translated_paragraphs or [],
                    translated_segments=translated_segments or [],
                    provider=provider
                )
                db.add(translation)
            
            db.commit()
            db.refresh(translation)
            
            return {
                'id': translation.id,
                'transcript_id': translation.transcript_id,
                'target_language': translation.target_language,
                'created_at': translation.created_at.isoformat() if translation.created_at else None
            }
            
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to save translation: {str(e)}")
        finally:
            db.close()
    
    def get_translations(
        self,
        user_id: int,
        transcript_id: int,
        target_language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get translations for a transcript (user-isolated)
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID
            target_language: Optional target language filter
            
        Returns:
            List of translation dictionaries
        """
        db: Session = self.SessionLocal()
        try:
            query = db.query(Translation).filter(
                and_(Translation.transcript_id == transcript_id, Translation.user_id == user_id)
            )
            
            if target_language:
                query = query.filter(Translation.target_language == target_language)
            
            translations = query.order_by(Translation.created_at.desc()).all()
            
            return [
                {
                    'id': t.id,
                    'transcript_id': t.transcript_id,
                    'source_language': t.source_language,
                    'target_language': t.target_language,
                    'translated_text': t.translated_text,
                    'translated_paragraphs': t.translated_paragraphs,
                    'translated_segments': t.translated_segments,
                    'provider': t.provider,
                    'created_at': t.created_at.isoformat() if t.created_at else None
                }
                for t in translations
            ]
        finally:
            db.close()
    
    def get_transcript(self, user_id: int, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get transcript by document ID (user-isolated)
        
        Args:
            user_id: User ID
            document_id: Document ID
            
        Returns:
            Transcript dictionary or None if not found
        """
        db: Session = self.SessionLocal()
        try:
            transcript = db.query(Transcript).filter(
                and_(Transcript.document_id == document_id, Transcript.user_id == user_id)
            ).first()
            
            if not transcript:
                return None
            
            return self._transcript_to_dict(transcript)
        finally:
            db.close()
    
    def get_user_transcripts(
        self,
        user_id: int,
        limit: Optional[int] = None,
        offset: int = 0,
        language: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all transcripts for user (user-isolated)
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            offset: Offset for pagination
            language: Filter by language code
            
        Returns:
            List of transcript dictionaries
        """
        db: Session = self.SessionLocal()
        try:
            query = db.query(Transcript).filter(Transcript.user_id == user_id)
            
            if language:
                query = query.filter(Transcript.language == language)
            
            query = query.order_by(Transcript.created_at.desc())
            
            if limit:
                query = query.limit(limit).offset(offset)
            
            transcripts = query.all()
            return [self._transcript_to_dict(t) for t in transcripts]
        finally:
            db.close()
    
    def _transcript_to_dict(self, transcript: Transcript) -> Dict[str, Any]:
        """Convert transcript model to dictionary"""
        return {
            'id': transcript.id,
            'document_id': transcript.document_id,
            'user_id': transcript.user_id,
            'source_file': transcript.source_file,
            'source_url': transcript.source_url,
            'source_type': transcript.source_type,
            'text': transcript.text,
            'language': transcript.language,
            'model_used': transcript.model_used,
            'paragraphs': transcript.paragraphs or [],
            'segments': transcript.segments or [],
            'created_at': transcript.created_at.isoformat() if transcript.created_at else None,
            'updated_at': transcript.updated_at.isoformat() if transcript.updated_at else None
        }
    
    def save_note(
        self,
        user_id: int,
        transcript_id: int,
        content: str,
        language: str,
        note_type: str = 'summary'
    ) -> Dict[str, Any]:
        """
        Save canonical note (generated once, in original language)
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID
            content: Note content
            language: Language of note (same as transcript)
            note_type: Type of note ('summary', 'key_points', 'custom')
            
        Returns:
            Dictionary with note data
        """
        db: Session = self.SessionLocal()
        try:
            # Verify transcript belongs to user
            transcript = db.query(Transcript).filter(
                and_(Transcript.id == transcript_id, Transcript.user_id == user_id)
            ).first()
            
            if not transcript:
                raise ValueError("Transcript not found or access denied")
            
            # Create new note
            note = Note(
                transcript_id=transcript_id,
                user_id=user_id,
                content=content,
                language=language,
                note_type=note_type
            )
            
            db.add(note)
            db.commit()
            db.refresh(note)
            
            return {
                'id': note.id,
                'transcript_id': note.transcript_id,
                'content': note.content,
                'language': note.language,
                'note_type': note.note_type,
                'created_at': note.created_at.isoformat() if note.created_at else None
            }
            
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to save note: {str(e)}")
        finally:
            db.close()
    
    def get_transcript_notes(self, user_id: int, transcript_id: int) -> List[Dict[str, Any]]:
        """
        Get all notes for a transcript (user-isolated)
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID
            
        Returns:
            List of note dictionaries
        """
        db: Session = self.SessionLocal()
        try:
            notes = db.query(Note).filter(
                and_(Note.transcript_id == transcript_id, Note.user_id == user_id)
            ).all()
            
            return [
                {
                    'id': note.id,
                    'transcript_id': note.transcript_id,
                    'content': note.content,
                    'language': note.language,
                    'note_type': note.note_type,
                    'created_at': note.created_at.isoformat() if note.created_at else None
                }
                for note in notes
            ]
        finally:
            db.close()
    
    def get_user_notes(self, user_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all notes for user (user-isolated)
        
        Args:
            user_id: User ID
            limit: Maximum number of results
            
        Returns:
            List of note dictionaries
        """
        db: Session = self.SessionLocal()
        try:
            query = db.query(Note).filter(Note.user_id == user_id)
            query = query.order_by(Note.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            notes = query.all()
            return [
                {
                    'id': note.id,
                    'transcript_id': note.transcript_id,
                    'content': note.content,
                    'language': note.language,
                    'note_type': note.note_type,
                    'created_at': note.created_at.isoformat() if note.created_at else None
                }
                for note in notes
            ]
        finally:
            db.close()
    
    def save_export_file(
        self,
        user_id: int,
        file_path: str,
        file_type: str,  # 'subtitle', 'document', 'audio'
        file_format: str,  # 'srt', 'vtt', 'md', 'txt', 'json', 'mp3', 'wav'
        transcript_id: Optional[int] = None,
        language: Optional[str] = None,
        is_translated: bool = False,
        file_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Save export file metadata to database
        
        Args:
            user_id: User ID
            file_path: Relative path from exports directory
            file_type: Type of export ('subtitle', 'document', 'audio')
            file_format: File format ('srt', 'vtt', 'md', 'txt', 'json', 'mp3', 'wav')
            transcript_id: Optional transcript ID this export is linked to
            language: Optional language code if translated
            is_translated: Whether this is a translation export
            file_size: File size in bytes
            
        Returns:
            Export file dictionary
        """
        db: Session = self.SessionLocal()
        try:
            export_file = ExportFile(
                user_id=user_id,
                transcript_id=transcript_id,
                file_path=file_path,
                file_type=file_type,
                file_format=file_format,
                language=language,
                is_translated=is_translated,
                file_size=file_size
            )
            db.add(export_file)
            db.commit()
            db.refresh(export_file)
            
            return {
                'id': export_file.id,
                'transcript_id': export_file.transcript_id,
                'file_path': export_file.file_path,
                'file_type': export_file.file_type,
                'file_format': export_file.file_format,
                'language': export_file.language,
                'is_translated': export_file.is_translated,
                'file_size': export_file.file_size,
                'created_at': export_file.created_at.isoformat() if export_file.created_at else None
            }
        finally:
            db.close()
    
    def get_user_exports(
        self,
        user_id: int,
        transcript_id: Optional[int] = None,
        file_type: Optional[str] = None,  # 'subtitle', 'document', 'audio'
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get export files for user (user-isolated)
        
        Args:
            user_id: User ID
            transcript_id: Optional transcript ID to filter by
            file_type: Optional file type to filter by
            limit: Maximum number of results
            
        Returns:
            List of export file dictionaries
        """
        db: Session = self.SessionLocal()
        try:
            query = db.query(ExportFile).filter(ExportFile.user_id == user_id)
            
            if transcript_id:
                query = query.filter(ExportFile.transcript_id == transcript_id)
            
            if file_type:
                query = query.filter(ExportFile.file_type == file_type)
            
            query = query.order_by(ExportFile.created_at.desc())
            
            if limit:
                query = query.limit(limit)
            
            exports = query.all()
            return [
                {
                    'id': exp.id,
                    'transcript_id': exp.transcript_id,
                    'file_path': exp.file_path,
                    'file_type': exp.file_type,
                    'file_format': exp.file_format,
                    'language': exp.language,
                    'is_translated': exp.is_translated,
                    'file_size': exp.file_size,
                    'created_at': exp.created_at.isoformat() if exp.created_at else None
                }
                for exp in exports
            ]
        finally:
            db.close()
    
    def delete_transcript(
        self,
        user_id: int,
        transcript_id: int
    ) -> bool:
        """
        Delete a transcript and all related data (translations, notes, tags, export files)
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        import os
        db: Session = self.SessionLocal()
        try:
            # Get transcript and verify ownership
            transcript = db.query(Transcript).filter(
                and_(Transcript.id == transcript_id, Transcript.user_id == user_id)
            ).first()
            
            if not transcript:
                return False
            
            # Delete associated export files (both database records and physical files)
            export_files = db.query(ExportFile).filter(
                and_(ExportFile.transcript_id == transcript_id, ExportFile.user_id == user_id)
            ).all()
            
            for export_file in export_files:
                # Delete physical file if it exists
                file_path = Config.EXPORTS_DIR / export_file.file_path
                if file_path.exists() and file_path.is_file():
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        print(f"Warning: Failed to delete export file {file_path}: {e}")
                
                # Delete database record
                db.delete(export_file)
            
            # Delete transcript (cascade will handle translations, notes, tags)
            db.delete(transcript)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error deleting transcript: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            db.close()
    
    def delete_export_file(
        self,
        user_id: int,
        export_id: int
    ) -> bool:
        """
        Delete an export file record and optionally the file itself
        
        Args:
            user_id: User ID
            export_id: Export file ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        import os
        
        db: Session = self.SessionLocal()
        try:
            # Get export and verify ownership
            export_file = db.query(ExportFile).filter(
                and_(ExportFile.id == export_id, ExportFile.user_id == user_id)
            ).first()
            
            if not export_file:
                return False
            
            # Delete the physical file if it exists
            file_path = Config.EXPORTS_DIR / export_file.file_path
            if file_path.exists() and file_path.is_file():
                try:
                    os.remove(file_path)
                except Exception as e:
                    print(f"Warning: Failed to delete file {file_path}: {e}")
            
            # Delete database record
            db.delete(export_file)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error deleting export file: {e}")
            return False
        finally:
            db.close()
    
    def delete_export_file_by_path(
        self,
        user_id: int,
        file_path: str
    ) -> bool:
        """
        Delete an export file by path (for files not in database)
        
        Args:
            user_id: User ID
            file_path: Relative file path (e.g., 'subtitles/file.srt')
            
        Returns:
            True if successful, False otherwise
        """
        import os
        
        try:
            # Security: ensure path is within exports directory
            full_path = Config.EXPORTS_DIR / file_path
            try:
                full_path.resolve().relative_to(Config.EXPORTS_DIR.resolve())
            except ValueError:
                return False  # Invalid path
            
            if full_path.exists() and full_path.is_file():
                os.remove(full_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting export file by path: {e}")
            return False
    
    def save_subtitle_transcript(
        self,
        user_id: int,
        text: str,
        segments: List[Dict],
        source_file: str,
        language: Optional[str] = None,
        name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save subtitle file as transcript - SUBTITLE-SPECIFIC HANDLER
        
        This function is ONLY for subtitle uploads (.srt/.vtt files).
        It bypasses all audio/video transcription logic and ensures
        language is ALWAYS set (defaults to 'en' if not provided).
        
        Args:
            user_id: User ID (for isolation)
            text: Extracted text from subtitle file
            segments: List of subtitle segments with timestamps
            source_file: Path to subtitle file
            language: Language code (optional, defaults to 'en' if not provided)
            name: Optional custom name for the transcript
            
        Returns:
            Dictionary with document_id and transcript data
            
        Raises:
            ValueError: If language cannot be determined (should never happen)
        """
        # CRITICAL: For subtitles, language MUST be set - default to 'en' if not provided
        # Subtitle files don't contain language metadata, so we use a safe default
        if not language or language.strip() == '' or language.lower() in ('none', 'null', 'auto'):
            language = 'en'  # Safe default for subtitles
        
        # Ensure language is a valid string
        language = str(language).strip()
        if not language:
            language = 'en'
        
        print(f"📝 save_subtitle_transcript: language={language} (guaranteed non-None), source_file={source_file}")
        
        db: Session = self.SessionLocal()
        try:
            # Generate unique document ID
            document_id = self._generate_document_id()
            max_retries = 10
            retry_count = 0
            while db.query(Transcript).filter(Transcript.document_id == document_id).first():
                retry_count += 1
                if retry_count >= max_retries:
                    raise ValueError("Failed to generate unique document ID after multiple attempts")
                document_id = self._generate_document_id()
            
            # Create transcript with subtitle-specific metadata
            # CRITICAL: language is guaranteed to be 'en' or a valid language code (never None)
            transcript = Transcript(
                document_id=document_id,
                user_id=user_id,
                source_file=source_file,
                source_url=None,
                source_type="subtitle",  # Explicitly set as subtitle
                text=text,
                language=language,  # Guaranteed to be valid string, never None
                model_used="subtitle_import",  # Indicates this came from subtitle file
                paragraphs=[],  # Subtitles use segments, not paragraphs
                segments=segments or []
            )
            
            db.add(transcript)
            db.commit()
            db.refresh(transcript)
            
            return {
                'document_id': transcript.document_id,
                'id': transcript.id,
                'user_id': transcript.user_id,
                'created_at': transcript.created_at.isoformat() if transcript.created_at else None
            }
            
        except IntegrityError as e:
            db.rollback()
            error_str = str(e).lower()
            
            # If language is None, this is a critical bug (should never happen)
            if 'not null' in error_str and 'language' in error_str:
                raise ValueError(
                    f"CRITICAL BUG: Language validation failed in save_subtitle_transcript. "
                    f"Language was: {repr(language)}. This should never happen."
                )
            
            # For other integrity errors, raise without retry
            raise ValueError(f"Database integrity error: {str(e)}")
        except Exception as e:
            db.rollback()
            print(f"❌ save_subtitle_transcript error: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to save subtitle transcript: {str(e)}")
        finally:
            db.close()
    
    def delete_note(self, user_id: int, note_id: int) -> bool:
        """
        Delete a note
        
        Args:
            user_id: User ID
            note_id: Note ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        db: Session = self.SessionLocal()
        try:
            # Get note and verify ownership
            note = db.query(Note).filter(
                and_(Note.id == note_id, Note.user_id == user_id)
            ).first()
            
            if not note:
                return False
            
            # Delete note (cascade will handle NoteTag relationships)
            db.delete(note)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error deleting note: {e}")
            return False
        finally:
            db.close()
    
    def delete_tag(self, user_id: int, tag_id: int) -> bool:
        """
        Delete a tag (will cascade delete TranscriptTag and NoteTag relationships)
        
        Args:
            user_id: User ID
            tag_id: Tag ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        db: Session = self.SessionLocal()
        try:
            # Get tag and verify ownership
            tag = db.query(Tag).filter(
                and_(Tag.id == tag_id, Tag.user_id == user_id)
            ).first()
            
            if not tag:
                return False
            
            # Delete tag (cascade will handle TranscriptTag and NoteTag relationships)
            db.delete(tag)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error deleting tag: {e}")
            return False
        finally:
            db.close()
    
    def remove_tag_from_transcript(self, user_id: int, transcript_id: int, tag_id: int) -> bool:
        """
        Remove a tag from a transcript (without deleting the tag itself)
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID
            tag_id: Tag ID to remove
            
        Returns:
            True if successful, False otherwise
        """
        db: Session = self.SessionLocal()
        try:
            # Find and delete the TranscriptTag relationship
            transcript_tag = db.query(TranscriptTag).filter(
                and_(
                    TranscriptTag.transcript_id == transcript_id,
                    TranscriptTag.tag_id == tag_id,
                    TranscriptTag.user_id == user_id
                )
            ).first()
            
            if not transcript_tag:
                return False
            
            db.delete(transcript_tag)
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error removing tag from transcript: {e}")
            return False
        finally:
            db.close()
    
    # ==================== Conversation Management ====================
    
    def create_conversation(
        self,
        user_id: int,
        session_id: Optional[str] = None,
        title: Optional[str] = None,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new conversation session
        
        Args:
            user_id: User ID
            session_id: Optional session ID (auto-generated if not provided)
            title: Optional conversation title (auto-generated from first question if not provided)
            language: Optional primary language of conversation
            
        Returns:
            Dictionary with conversation_id, session_id, created_at
        """
        db: Session = self.SessionLocal()
        try:
            if not session_id:
                session_id = secrets.token_urlsafe(32)
            
            conversation = Conversation(
                session_id=session_id,
                user_id=user_id,
                title=title,
                language=language
            )
            
            db.add(conversation)
            db.commit()
            db.refresh(conversation)
            
            return {
                'conversation_id': conversation.id,
                'session_id': conversation.session_id,
                'title': conversation.title,
                'language': conversation.language,
                'created_at': conversation.created_at.isoformat() if conversation.created_at else None
            }
        except IntegrityError:
            db.rollback()
            # Session ID already exists, try again with new ID
            return self.create_conversation(user_id, None, title, language)
        except Exception as e:
            db.rollback()
            print(f"Error creating conversation: {e}")
            raise
        finally:
            db.close()
    
    def get_conversation(
        self,
        user_id: int,
        session_id: Optional[str] = None,
        conversation_id: Optional[int] = None,
        limit_messages: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Get conversation by session_id or conversation_id
        
        Args:
            user_id: User ID
            session_id: Session ID (optional)
            conversation_id: Conversation ID (optional)
            limit_messages: Maximum number of messages to load (default: 100)
            
        Returns:
            Conversation dictionary with messages, or None if not found
        """
        db: Session = self.SessionLocal()
        try:
            if session_id:
                conversation = db.query(Conversation).filter(
                    and_(
                        Conversation.session_id == session_id,
                        Conversation.user_id == user_id
                    )
                ).first()
            elif conversation_id:
                conversation = db.query(Conversation).filter(
                    and_(
                        Conversation.id == conversation_id,
                        Conversation.user_id == user_id
                    )
                ).first()
            else:
                return None
            
            if not conversation:
                return None
            
            # Get messages with limit - only load recent messages for performance
            # Order by created_at DESC to get most recent, then reverse to show chronologically
            messages = db.query(ConversationMessage).filter(
                ConversationMessage.conversation_id == conversation.id
            ).order_by(ConversationMessage.created_at.desc()).limit(limit_messages).all()
            
            # Reverse to show in chronological order (oldest first)
            messages = list(reversed(messages))
            
            # Get total message count for pagination info
            total_messages = db.query(func.count(ConversationMessage.id)).filter(
                ConversationMessage.conversation_id == conversation.id
            ).scalar()
            
            return {
                'conversation_id': conversation.id,
                'session_id': conversation.session_id,
                'title': conversation.title,
                'language': conversation.language,
                'created_at': conversation.created_at.isoformat() if conversation.created_at else None,
                'updated_at': conversation.updated_at.isoformat() if conversation.updated_at else None,
                'messages': [
                    {
                        'id': msg.id,
                        'role': msg.role,
                        'content': msg.content,
                        'metadata': msg.message_metadata or {},
                        'created_at': msg.created_at.isoformat() if msg.created_at else None
                    }
                    for msg in messages
                ],
                'total_messages': total_messages,
                'loaded_messages': len(messages)
            }
        except Exception as e:
            print(f"Error getting conversation: {e}")
            return None
        finally:
            db.close()
    
    def get_user_conversations(
        self,
        user_id: int,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get all conversations for a user (most recent first)
        
        Args:
            user_id: User ID
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversation dictionaries (without messages)
        """
        db: Session = self.SessionLocal()
        try:
            # Use a JOIN with COUNT to efficiently count messages in a single query
            # This avoids N+1 query problem when accessing conv.messages
            conversations = db.query(
                Conversation,
                func.count(ConversationMessage.id).label('message_count')
            ).outerjoin(
                ConversationMessage,
                Conversation.id == ConversationMessage.conversation_id
            ).filter(
                Conversation.user_id == user_id
            ).group_by(Conversation.id).order_by(
                Conversation.updated_at.desc()
            ).limit(limit).all()
            
            return [
                {
                    'conversation_id': conv.id,
                    'session_id': conv.session_id,
                    'title': conv.title,
                    'language': conv.language,
                    'created_at': conv.created_at.isoformat() if conv.created_at else None,
                    'updated_at': conv.updated_at.isoformat() if conv.updated_at else None,
                    'message_count': count  # Use the count from the query
                }
                for conv, count in conversations
            ]
        except Exception as e:
            print(f"Error getting user conversations: {e}")
            return []
        finally:
            db.close()
    
    def add_message(
        self,
        user_id: int,
        conversation_id: int,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a message to a conversation
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (citations, chunks, etc.)
            
        Returns:
            Dictionary with message_id, created_at
        """
        db: Session = self.SessionLocal()
        try:
            # Verify conversation belongs to user
            conversation = db.query(Conversation).filter(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
            ).first()
            
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found or doesn't belong to user {user_id}")
            
            # Create message
            message = ConversationMessage(
                conversation_id=conversation_id,
                user_id=user_id,
                role=role,
                content=content,
                message_metadata=metadata
            )
            
            db.add(message)
            
            # Update conversation timestamp and title if first message
            conversation.updated_at = datetime.utcnow()
            if not conversation.title and role == 'user':
                # Auto-generate title from first question (first 50 chars)
                conversation.title = content[:50] + ('...' if len(content) > 50 else '')
            
            db.commit()
            db.refresh(message)
            
            return {
                'message_id': message.id,
                'conversation_id': conversation_id,
                'role': message.role,
                'content': message.content,
                'metadata': message.message_metadata or {},
                'created_at': message.created_at.isoformat() if message.created_at else None
            }
        except Exception as e:
            db.rollback()
            print(f"Error adding message: {e}")
            raise
        finally:
            db.close()
    
    def delete_conversation(
        self,
        user_id: int,
        conversation_id: int
    ) -> bool:
        """
        Delete a conversation and all its messages
        
        Args:
            user_id: User ID
            conversation_id: Conversation ID
            
        Returns:
            True if deleted, False if not found
        """
        db: Session = self.SessionLocal()
        try:
            conversation = db.query(Conversation).filter(
                and_(
                    Conversation.id == conversation_id,
                    Conversation.user_id == user_id
                )
            ).first()
            
            if not conversation:
                return False
            
            db.delete(conversation)  # Cascade will delete messages
            db.commit()
            return True
        except Exception as e:
            db.rollback()
            print(f"Error deleting conversation: {e}")
            return False
        finally:
            db.close()