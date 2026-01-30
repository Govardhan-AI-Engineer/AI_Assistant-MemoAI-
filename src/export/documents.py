"""
Document export module (Markdown, Plain Text, JSON)
Task 4: Export & Output
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from src.core.config import Config
from src.core.exceptions import TranscriptionError


class DocumentExporter:
    """Export transcripts and translations to various document formats"""
    
    @staticmethod
    def _format_timestamp(seconds: float) -> str:
        """
        Format seconds to readable timestamp (HH:MM:SS)
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def export_markdown(
        transcription_data: Dict,
        output_path: Optional[Path] = None,
        source_file: Optional[Path] = None,
        translated_text: Optional[str] = None,
        translated_paragraphs: Optional[List[Dict]] = None,
        include_timestamps: bool = True,
        include_metadata: bool = True
    ) -> Path:
        """
        Export transcription to Markdown format
        
        Args:
            transcription_data: Transcription result dictionary
            output_path: Optional output file path
            source_file: Original source file (for naming)
            translated_text: Optional translated text
            translated_paragraphs: Optional translated paragraphs with timestamps
            include_timestamps: Include timestamps in output
            include_metadata: Include metadata header
            
        Returns:
            Path to generated Markdown file
        """
        if output_path is None:
            if source_file:
                base_name = source_file.stem
            else:
                base_name = f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            output_path = Config.EXPORTS_DIR / "documents" / f"{base_name}.md"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build Markdown content
        md_lines = []
        
        # Header with metadata
        if include_metadata:
            md_lines.append("# Transcription")
            md_lines.append("")
            
            metadata = transcription_data.get('metadata', {})
            if metadata:
                md_lines.append("## Metadata")
                md_lines.append("")
                if metadata.get('source_file'):
                    md_lines.append(f"- **Source File**: `{metadata['source_file']}`")
                if metadata.get('source_url'):
                    md_lines.append(f"- **Source URL**: `{metadata['source_url']}`")
                if metadata.get('created_at'):
                    md_lines.append(f"- **Created**: {metadata['created_at']}")
                if metadata.get('model'):
                    md_lines.append(f"- **Model**: {metadata['model']}")
                
                language = transcription_data.get('language')
                if language:
                    md_lines.append(f"- **Language**: {language}")
                
                md_lines.append("")
        
        # ALWAYS include original transcription first
        original_text = transcription_data.get('text', '')
        original_paragraphs = transcription_data.get('paragraphs', [])
        
        # Export original transcription
        if original_paragraphs:
            # Export with paragraph structure
            md_lines.append("## Original Transcription")
            md_lines.append("")
            
            for para in original_paragraphs:
                para_text = para.get('text', '')
                if not para_text.strip():
                    continue
                
                if include_timestamps:
                    start_time = para.get('start', 0.0)
                    timestamp = DocumentExporter._format_timestamp(start_time)
                    md_lines.append(f"**[{timestamp}]** {para_text}")
                else:
                    md_lines.append(para_text)
                
                md_lines.append("")
        else:
            # Export as single text block
            md_lines.append("## Original Transcription")
            md_lines.append("")
            if original_text:
                md_lines.append(original_text)
            md_lines.append("")
        
        # Add translation section if translated text is provided
        if translated_text and translated_text != original_text:
            md_lines.append("---")
            md_lines.append("")
            md_lines.append("## Translation")
            md_lines.append("")
            
            # Check if we have translated paragraphs
            if translated_paragraphs:
                for para in translated_paragraphs:
                    para_text = para.get('translated_text', para.get('text', ''))
                    if not para_text.strip():
                        continue
                    
                    if include_timestamps:
                        start_time = para.get('start', 0.0)
                        timestamp = DocumentExporter._format_timestamp(start_time)
                        md_lines.append(f"**[{timestamp}]** {para_text}")
                    else:
                        md_lines.append(para_text)
                    
                    md_lines.append("")
            else:
                # Export as single text block
                md_lines.append(translated_text)
                md_lines.append("")
        
        # Write to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(md_lines))
            
            return output_path
        except Exception as e:
            raise TranscriptionError(f"Failed to export Markdown: {str(e)}")
    
    @staticmethod
    def export_text(
        transcription_data: Dict,
        output_path: Optional[Path] = None,
        source_file: Optional[Path] = None,
        translated_text: Optional[str] = None,
        translated_paragraphs: Optional[List[Dict]] = None,
        include_timestamps: bool = False
    ) -> Path:
        """
        Export transcription to plain text format
        
        Args:
            transcription_data: Transcription result dictionary
            output_path: Optional output file path
            source_file: Original source file (for naming)
            translated_text: Optional translated text
            translated_paragraphs: Optional translated paragraphs
            include_timestamps: Include timestamps in output
            
        Returns:
            Path to generated text file
        """
        if output_path is None:
            if source_file:
                base_name = source_file.stem
            else:
                base_name = f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            output_path = Config.EXPORTS_DIR / "documents" / f"{base_name}.txt"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build text content
        text_lines = []
        
        # ALWAYS include original transcription first
        original_text = transcription_data.get('text', '')
        original_paragraphs = transcription_data.get('paragraphs', [])
        
        # Export original transcription
        text_lines.append("=" * 70)
        text_lines.append("ORIGINAL TRANSCRIPTION")
        text_lines.append("=" * 70)
        text_lines.append("")
        
        if original_paragraphs:
            # Export with paragraph structure
            for para in original_paragraphs:
                para_text = para.get('text', '')
                if not para_text.strip():
                    continue
                
                if include_timestamps:
                    start_time = para.get('start', 0.0)
                    timestamp = DocumentExporter._format_timestamp(start_time)
                    text_lines.append(f"[{timestamp}] {para_text}")
                else:
                    text_lines.append(para_text)
                
                text_lines.append("")  # Empty line between paragraphs
        else:
            # Export as single text block
            if original_text:
                text_lines.append(original_text)
        
        # Add translation if provided
        if translated_text and translated_text != original_text:
            text_lines.append("")
            text_lines.append("=" * 70)
            text_lines.append("TRANSLATION")
            text_lines.append("=" * 70)
            text_lines.append("")
            
            # Check if we have translated paragraphs
            if translated_paragraphs:
                for para in translated_paragraphs:
                    para_text = para.get('translated_text', para.get('text', ''))
                    if not para_text.strip():
                        continue
                    
                    if include_timestamps:
                        start_time = para.get('start', 0.0)
                        timestamp = DocumentExporter._format_timestamp(start_time)
                        text_lines.append(f"[{timestamp}] {para_text}")
                    else:
                        text_lines.append(para_text)
                    
                    text_lines.append("")  # Empty line between paragraphs
            else:
                # Export as single text block
                text_lines.append(translated_text)
        
        # Write to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text_lines))
            
            return output_path
        except Exception as e:
            raise TranscriptionError(f"Failed to export text: {str(e)}")
    
    @staticmethod
    def export_json(
        transcription_data: Dict,
        output_path: Optional[Path] = None,
        source_file: Optional[Path] = None,
        translated_text: Optional[str] = None,
        translated_paragraphs: Optional[List[Dict]] = None,
        translated_segments: Optional[List[Dict]] = None,
        include_original: bool = True
    ) -> Path:
        """
        Export transcription to structured JSON format
        
        Args:
            transcription_data: Transcription result dictionary
            output_path: Optional output file path
            source_file: Original source file (for naming)
            translated_text: Optional translated text
            translated_paragraphs: Optional translated paragraphs
            translated_segments: Optional translated segments
            include_original: Include original text alongside translation
            
        Returns:
            Path to generated JSON file
        """
        if output_path is None:
            if source_file:
                base_name = source_file.stem
            else:
                base_name = f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            output_path = Config.EXPORTS_DIR / "documents" / f"{base_name}.json"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build JSON structure
        export_data = {
            'metadata': transcription_data.get('metadata', {}).copy(),
            'language': {
                'original': transcription_data.get('language'),
                'translated': None  # Will be set if translation provided
            },
            'text': {
                'original': transcription_data.get('text', ''),
                'translated': translated_text if translated_text else None
            },
            'segments': [],
            'paragraphs': []
        }
        
        # Add original segments
        if include_original:
            original_segments = transcription_data.get('segments', [])
            export_data['segments'].extend([
                {
                    'start': seg.get('start', 0.0),
                    'end': seg.get('end', 0.0),
                    'text': seg.get('text', '')
                }
                for seg in original_segments
            ])
        
        # Add translated segments if available
        if translated_segments:
            export_data['segments'].extend([
                {
                    'start': seg.get('start', 0.0),
                    'end': seg.get('end', 0.0),
                    'text': seg.get('translated_text', seg.get('text', '')),
                    'is_translation': True
                }
                for seg in translated_segments
            ])
        
        # Add original paragraphs
        if include_original:
            original_paragraphs = transcription_data.get('paragraphs', [])
            export_data['paragraphs'].extend([
                {
                    'start': para.get('start', 0.0),
                    'end': para.get('end', 0.0),
                    'text': para.get('text', '')
                }
                for para in original_paragraphs
            ])
        
        # Add translated paragraphs if available
        if translated_paragraphs:
            export_data['paragraphs'].extend([
                {
                    'start': para.get('start', 0.0),
                    'end': para.get('end', 0.0),
                    'text': para.get('translated_text', para.get('text', '')),
                    'is_translation': True
                }
                for para in translated_paragraphs
            ])
        
        # Add export metadata
        export_data['export_metadata'] = {
            'exported_at': datetime.now().isoformat(),
            'format': 'json',
            'includes_translation': translated_text is not None
        }
        
        # Write to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return output_path
        except Exception as e:
            raise TranscriptionError(f"Failed to export JSON: {str(e)}")
    
    @staticmethod
    def export_all(
        transcription_data: Dict,
        base_name: Optional[str] = None,
        source_file: Optional[Path] = None,
        translated_text: Optional[str] = None,
        translated_paragraphs: Optional[List[Dict]] = None,
        translated_segments: Optional[List[Dict]] = None,
        include_timestamps: bool = True
    ) -> Dict[str, Path]:
        """
        Export to all document formats (MD, TXT, JSON)
        
        Args:
            transcription_data: Transcription result dictionary
            base_name: Base name for output files
            source_file: Original source file
            translated_text: Optional translated text
            translated_paragraphs: Optional translated paragraphs
            translated_segments: Optional translated segments
            include_timestamps: Include timestamps in MD/TXT
            
        Returns:
            Dictionary with 'md', 'txt', 'json' keys pointing to file paths
        """
        if base_name is None:
            if source_file:
                base_name = source_file.stem
            else:
                base_name = f"transcript_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        md_path = DocumentExporter.export_markdown(
            transcription_data,
            output_path=Config.EXPORTS_DIR / "documents" / f"{base_name}.md",
            source_file=source_file,
            translated_text=translated_text,
            translated_paragraphs=translated_paragraphs,
            include_timestamps=include_timestamps
        )
        
        txt_path = DocumentExporter.export_text(
            transcription_data,
            output_path=Config.EXPORTS_DIR / "documents" / f"{base_name}.txt",
            source_file=source_file,
            translated_text=translated_text,
            translated_paragraphs=translated_paragraphs,
            include_timestamps=include_timestamps
        )
        
        json_path = DocumentExporter.export_json(
            transcription_data,
            output_path=Config.EXPORTS_DIR / "documents" / f"{base_name}.json",
            source_file=source_file,
            translated_text=translated_text,
            translated_paragraphs=translated_paragraphs,
            translated_segments=translated_segments
        )
        
        return {
            'md': md_path,
            'txt': txt_path,
            'json': json_path
        }
