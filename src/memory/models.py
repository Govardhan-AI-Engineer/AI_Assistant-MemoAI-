"""
Database models for persistent memory storage
All models include user_id for data isolation
"""
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, 
    Boolean, Float, JSON, Index
)
from sqlalchemy.orm import relationship
from datetime import datetime
from typing import Optional, Dict, Any

# Import Base from core to ensure shared database
from src.core.database import Base


class Transcript(Base):
    """
    Immutable transcript document
    Each transcription is stored as a separate document with unique document_id
    """
    __tablename__ = 'transcripts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(String(64), unique=True, nullable=False, index=True)  # Unique document ID
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Source metadata
    source_file = Column(String(500), nullable=True)
    source_url = Column(String(1000), nullable=True)
    source_type = Column(String(50), nullable=False)  # 'file', 'url', 'subtitle'
    
    # Transcription data
    text = Column(Text, nullable=False)  # Full transcript text
    language = Column(String(10), nullable=False)  # Language code (e.g., 'hi', 'en', 'te')
    model_used = Column(String(50), nullable=True)  # Whisper model used
    
    # Paragraph-level data (stored as JSON)
    paragraphs = Column(JSON, nullable=True)  # List of paragraph dicts with text, start, end
    
    # Segments (stored as JSON)
    segments = Column(JSON, nullable=True)  # List of segment dicts with text, start, end
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    translations = relationship("Translation", back_populates="transcript", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="transcript", cascade="all, delete-orphan")
    tags = relationship("TranscriptTag", back_populates="transcript", cascade="all, delete-orphan")
    
    # Indexes for search
    __table_args__ = (
        Index('idx_transcript_user_created', 'user_id', 'created_at'),
        Index('idx_transcript_user_language', 'user_id', 'language'),
    )


class Translation(Base):
    """
    Translation linked to a transcript
    Supports multiple translations per transcript (different target languages)
    """
    __tablename__ = 'translations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transcript_id = Column(Integer, ForeignKey('transcripts.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Translation metadata
    source_language = Column(String(10), nullable=False)
    target_language = Column(String(10), nullable=False)
    provider = Column(String(50), nullable=True)  # 'google', 'libre', 'deepl', 'ai'
    
    # Translation data
    translated_text = Column(Text, nullable=False)
    translated_paragraphs = Column(JSON, nullable=True)  # Translated paragraphs with timestamps
    translated_segments = Column(JSON, nullable=True)  # Translated segments
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    transcript = relationship("Transcript", back_populates="translations")
    
    # Indexes
    __table_args__ = (
        Index('idx_translation_user_target', 'user_id', 'target_language'),
        Index('idx_translation_transcript', 'transcript_id', 'target_language'),
    )


class Note(Base):
    """
    Canonical AI-generated notes/summaries
    Generated once from original transcription language
    Translated on demand for display only
    """
    __tablename__ = 'notes'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transcript_id = Column(Integer, ForeignKey('transcripts.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Note content (canonical - in original transcript language)
    content = Column(Text, nullable=False)
    language = Column(String(10), nullable=False)  # Language of the note (same as transcript)
    
    # Note type
    note_type = Column(String(50), nullable=False, default='summary')  # 'summary', 'key_points', 'custom'
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transcript = relationship("Transcript", back_populates="notes")
    tags = relationship("NoteTag", back_populates="note", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_note_user_created', 'user_id', 'created_at'),
    )


class Tag(Base):
    """
    Tag for organizing content
    Tags are user-specific and reusable
    """
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(20), nullable=True)  # Optional color for UI
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    transcript_tags = relationship("TranscriptTag", back_populates="tag", cascade="all, delete-orphan")
    note_tags = relationship("NoteTag", back_populates="tag", cascade="all, delete-orphan")
    
    # Unique constraint: user_id + name
    __table_args__ = (
        Index('idx_tag_user_name', 'user_id', 'name', unique=True),
    )


class TranscriptTag(Base):
    """
    Many-to-many relationship between transcripts and tags
    """
    __tablename__ = 'transcript_tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transcript_id = Column(Integer, ForeignKey('transcripts.id'), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey('tags.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    transcript = relationship("Transcript", back_populates="tags")
    tag = relationship("Tag", back_populates="transcript_tags")
    
    # Unique constraint: transcript + tag
    __table_args__ = (
        Index('idx_transcript_tag_unique', 'transcript_id', 'tag_id', unique=True),
    )


class NoteTag(Base):
    """
    Many-to-many relationship between notes and tags
    """
    __tablename__ = 'note_tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    note_id = Column(Integer, ForeignKey('notes.id'), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey('tags.id'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    note = relationship("Note", back_populates="tags")
    tag = relationship("Tag", back_populates="note_tags")
    
    # Unique constraint: note + tag
    __table_args__ = (
        Index('idx_note_tag_unique', 'note_id', 'tag_id', unique=True),
    )


class ExportFile(Base):
    """
    Track exported files (subtitles, documents, audio)
    Ensures user isolation and provides metadata
    """
    __tablename__ = 'export_files'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    transcript_id = Column(Integer, ForeignKey('transcripts.id'), nullable=True, index=True)  # Optional - may be batch export
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # File metadata
    file_path = Column(String(1000), nullable=False)  # Relative path from exports directory
    file_type = Column(String(50), nullable=False)  # 'subtitle', 'document', 'audio'
    file_format = Column(String(20), nullable=False)  # 'srt', 'vtt', 'md', 'txt', 'json', 'mp3', 'wav'
    file_size = Column(Integer, nullable=True)  # Size in bytes
    
    # Export metadata
    language = Column(String(10), nullable=True)  # Language code if translated
    is_translated = Column(Boolean, default=False)  # Whether this is a translation export
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    transcript = relationship("Transcript")
    
    # Indexes
    __table_args__ = (
        Index('idx_export_user_type', 'user_id', 'file_type'),
        Index('idx_export_transcript', 'transcript_id', 'file_type'),
    )
