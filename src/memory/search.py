"""
Search service for full-text search and tag-based filtering
All searches are user-isolated
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, Session

from src.memory.models import Transcript, Note, Tag, TranscriptTag, NoteTag
from src.core.config import Config


class SearchService:
    """
    Search service with full-text search and tag filtering
    All searches are restricted to user's data
    """
    
    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize search service
        
        Args:
            database_url: Database URL (defaults to Config.DATABASE_URL)
        """
        self.database_url = database_url or Config.DATABASE_URL
        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def search_transcripts(
        self,
        user_id: int,
        query: str,
        language: Optional[str] = None,
        tag_names: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Full-text search over transcripts (user-isolated)
        
        Args:
            user_id: User ID
            query: Search query
            language: Filter by language code
            tag_names: Filter by tag names
            limit: Maximum number of results
            
        Returns:
            List of matching transcript dictionaries
        """
        db: Session = self.SessionLocal()
        try:
            # Base query - user isolation
            base_query = db.query(Transcript).filter(Transcript.user_id == user_id)
            
            # Text search (case-insensitive)
            if query:
                search_term = f"%{query.lower()}%"
                base_query = base_query.filter(
                    or_(
                        Transcript.text.ilike(search_term),
                        func.lower(Transcript.source_file).like(search_term) if Transcript.source_file else False,
                        func.lower(Transcript.source_url).like(search_term) if Transcript.source_url else False
                    )
                )
            
            # Language filter
            if language:
                base_query = base_query.filter(Transcript.language == language)
            
            # Tag filter
            if tag_names:
                # Get tag IDs for user
                tag_ids = db.query(Tag.id).filter(
                    and_(Tag.user_id == user_id, Tag.name.in_(tag_names))
                ).subquery()
                
                # Get transcript IDs with these tags
                transcript_ids = db.query(TranscriptTag.transcript_id).filter(
                    TranscriptTag.tag_id.in_(tag_ids)
                ).subquery()
                
                base_query = base_query.filter(Transcript.id.in_(transcript_ids))
            
            # Order by relevance (most recent first)
            results = base_query.order_by(Transcript.created_at.desc()).limit(limit).all()
            
            return [
                {
                    'id': t.id,
                    'document_id': t.document_id,
                    'text': t.text[:200] + '...' if len(t.text) > 200 else t.text,  # Preview
                    'language': t.language,
                    'source_file': t.source_file,
                    'source_url': t.source_url,
                    'created_at': t.created_at.isoformat() if t.created_at else None
                }
                for t in results
            ]
        finally:
            db.close()
    
    def search_notes(
        self,
        user_id: int,
        query: str,
        tag_names: Optional[List[str]] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Full-text search over notes (user-isolated)
        
        Args:
            user_id: User ID
            query: Search query
            tag_names: Filter by tag names
            limit: Maximum number of results
            
        Returns:
            List of matching note dictionaries
        """
        db: Session = self.SessionLocal()
        try:
            # Base query - user isolation
            base_query = db.query(Note).filter(Note.user_id == user_id)
            
            # Text search (case-insensitive)
            if query:
                search_term = f"%{query.lower()}%"
                base_query = base_query.filter(Note.content.ilike(search_term))
            
            # Tag filter
            if tag_names:
                # Get tag IDs for user
                tag_ids = db.query(Tag.id).filter(
                    and_(Tag.user_id == user_id, Tag.name.in_(tag_names))
                ).subquery()
                
                # Get note IDs with these tags
                note_ids = db.query(NoteTag.note_id).filter(
                    NoteTag.tag_id.in_(tag_ids)
                ).subquery()
                
                base_query = base_query.filter(Note.id.in_(note_ids))
            
            # Order by relevance (most recent first)
            results = base_query.order_by(Note.created_at.desc()).limit(limit).all()
            
            return [
                {
                    'id': n.id,
                    'transcript_id': n.transcript_id,
                    'content': n.content[:200] + '...' if len(n.content) > 200 else n.content,  # Preview
                    'language': n.language,
                    'note_type': n.note_type,
                    'created_at': n.created_at.isoformat() if n.created_at else None
                }
                for n in results
            ]
        finally:
            db.close()
    
    def get_tags(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Get all tags for user
        
        Args:
            user_id: User ID
            
        Returns:
            List of tag dictionaries
        """
        db: Session = self.SessionLocal()
        try:
            tags = db.query(Tag).filter(Tag.user_id == user_id).order_by(Tag.name).all()
            
            return [
                {
                    'id': tag.id,
                    'name': tag.name,
                    'color': tag.color,
                    'created_at': tag.created_at.isoformat() if tag.created_at else None
                }
                for tag in tags
            ]
        finally:
            db.close()
    
    def create_tag(self, user_id: int, name: str, color: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new tag for user
        
        Args:
            user_id: User ID
            name: Tag name
            color: Optional color
            
        Returns:
            Tag dictionary
        """
        db: Session = self.SessionLocal()
        try:
            # Check if tag already exists
            existing = db.query(Tag).filter(
                and_(Tag.user_id == user_id, Tag.name == name)
            ).first()
            
            if existing:
                return {
                    'id': existing.id,
                    'name': existing.name,
                    'color': existing.color,
                    'created_at': existing.created_at.isoformat() if existing.created_at else None
                }
            
            # Create new tag
            tag = Tag(user_id=user_id, name=name, color=color)
            db.add(tag)
            db.commit()
            db.refresh(tag)
            
            return {
                'id': tag.id,
                'name': tag.name,
                'color': tag.color,
                'created_at': tag.created_at.isoformat() if tag.created_at else None
            }
        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create tag: {str(e)}")
        finally:
            db.close()
    
    def add_tag_to_transcript(
        self,
        user_id: int,
        transcript_id: int,
        tag_id: int
    ) -> bool:
        """
        Add tag to transcript
        
        Args:
            user_id: User ID
            transcript_id: Transcript ID
            tag_id: Tag ID
            
        Returns:
            True if successful
        """
        db: Session = self.SessionLocal()
        try:
            # Verify ownership
            transcript = db.query(Transcript).filter(
                and_(Transcript.id == transcript_id, Transcript.user_id == user_id)
            ).first()
            
            tag = db.query(Tag).filter(
                and_(Tag.id == tag_id, Tag.user_id == user_id)
            ).first()
            
            if not transcript or not tag:
                return False
            
            # Check if already tagged
            existing = db.query(TranscriptTag).filter(
                and_(
                    TranscriptTag.transcript_id == transcript_id,
                    TranscriptTag.tag_id == tag_id
                )
            ).first()
            
            if existing:
                return True  # Already tagged
            
            # Add tag
            transcript_tag = TranscriptTag(
                transcript_id=transcript_id,
                tag_id=tag_id,
                user_id=user_id
            )
            db.add(transcript_tag)
            db.commit()
            
            return True
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()
    
    def add_tag_to_note(
        self,
        user_id: int,
        note_id: int,
        tag_id: int
    ) -> bool:
        """
        Add tag to note
        
        Args:
            user_id: User ID
            note_id: Note ID
            tag_id: Tag ID
            
        Returns:
            True if successful
        """
        db: Session = self.SessionLocal()
        try:
            # Verify ownership
            note = db.query(Note).filter(
                and_(Note.id == note_id, Note.user_id == user_id)
            ).first()
            
            tag = db.query(Tag).filter(
                and_(Tag.id == tag_id, Tag.user_id == user_id)
            ).first()
            
            if not note or not tag:
                return False
            
            # Check if already tagged
            existing = db.query(NoteTag).filter(
                and_(
                    NoteTag.note_id == note_id,
                    NoteTag.tag_id == tag_id
                )
            ).first()
            
            if existing:
                return True  # Already tagged
            
            # Add tag
            note_tag = NoteTag(
                note_id=note_id,
                tag_id=tag_id,
                user_id=user_id
            )
            db.add(note_tag)
            db.commit()
            
            return True
        except Exception as e:
            db.rollback()
            return False
        finally:
            db.close()
