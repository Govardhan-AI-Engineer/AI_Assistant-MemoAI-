"""
File handling utilities for transcription
"""
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
from src.core.config import Config
from src.core.exceptions import TranscriptionError


class TranscriptionFileHandler:
    """Handle saving and loading transcription results"""
    
    @staticmethod
    def save_transcription(
        transcription_data: Dict,
        output_path: Optional[Path] = None,
        source_file: Optional[Path] = None
    ) -> Path:
        """
        Save transcription to JSON file
        
        Args:
            transcription_data: Transcription result dictionary
            output_path: Optional output file path
            source_file: Original source file path (for naming)
            
        Returns:
            Path to saved file
        """
        if output_path is None:
            # Generate filename from source or timestamp
            if source_file:
                base_name = source_file.stem
            else:
                base_name = f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            output_path = Config.TRANSCRIPTS_DIR / f"{base_name}.json"
        
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Add metadata
        transcription_data['metadata'] = {
            'created_at': datetime.now().isoformat(),
            'source_file': str(source_file) if source_file else None,
            'model': transcription_data.get('full_result', {}).get('model', 'unknown')
        }
        
        # Save to JSON
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(transcription_data, f, indent=2, ensure_ascii=False)
            
            return output_path
        except Exception as e:
            raise TranscriptionError(f"Failed to save transcription: {str(e)}")
    
    @staticmethod
    def load_transcription(file_path: Path) -> Dict:
        """
        Load transcription from JSON file
        
        Args:
            file_path: Path to transcription JSON file
            
        Returns:
            Transcription data dictionary
        """
        if not file_path.exists():
            raise TranscriptionError(f"Transcription file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise TranscriptionError(f"Failed to load transcription: {str(e)}")
    
    @staticmethod
    def save_text_only(
        text: str,
        output_path: Optional[Path] = None,
        source_file: Optional[Path] = None
    ) -> Path:
        """
        Save transcription as plain text
        
        Args:
            text: Transcription text
            output_path: Optional output file path
            source_file: Original source file path (for naming)
            
        Returns:
            Path to saved file
        """
        if output_path is None:
            if source_file:
                base_name = source_file.stem
            else:
                base_name = f"transcription_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            output_path = Config.TRANSCRIPTS_DIR / f"{base_name}.txt"
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            
            return output_path
        except Exception as e:
            raise TranscriptionError(f"Failed to save text file: {str(e)}")
