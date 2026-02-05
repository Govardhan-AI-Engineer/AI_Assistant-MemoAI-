"""
Subtitle generation module (SRT & VTT)
Task 4: Export & Output
"""
from pathlib import Path
from typing import Dict, List, Optional
from datetime import timedelta
from src.core.config import Config
from src.core.exceptions import TranscriptionError


class SubtitleGenerator:
    """Generate SRT and VTT subtitle files from transcription results"""
    
    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        """
        Format seconds to SRT timestamp (HH:MM:SS,mmm)
        
        Args:
            seconds: Time in seconds
            
        Returns:
            SRT-formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        milliseconds = int((seconds - total_seconds) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    @staticmethod
    def _format_vtt_timestamp(seconds: float) -> str:
        """
        Format seconds to VTT timestamp (HH:MM:SS.mmm)
        
        Args:
            seconds: Time in seconds
            
        Returns:
            VTT-formatted timestamp string
        """
        td = timedelta(seconds=seconds)
        total_seconds = int(td.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        milliseconds = int((seconds - total_seconds) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"
    
    @staticmethod
    def _clean_text_for_subtitle(text: str) -> str:
        """
        Clean text for subtitle display (remove extra whitespace, handle line breaks)
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text suitable for subtitles
        """
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove HTML-like tags if any
        import re
        text = re.sub(r'<[^>]+>', '', text)
        return text.strip()
    
    @staticmethod
    def generate_srt(
        transcription_data: Dict,
        output_path: Optional[Path] = None,
        source_file: Optional[Path] = None,
        use_paragraphs: bool = False,
        translated_text: Optional[str] = None,
        translated_segments: Optional[List[Dict]] = None
    ) -> Path:
        """
        Generate SRT subtitle file from transcription
        
        Args:
            transcription_data: Transcription result dictionary with 'segments' or 'paragraphs'
            output_path: Optional output file path
            source_file: Original source file (for naming)
            use_paragraphs: Use paragraph-level segmentation instead of segments
            translated_text: Optional translated text (IGNORED if translated_segments is provided)
            translated_segments: Optional translated segments with timestamps (PREFERRED)
            
        Returns:
            Path to generated SRT file
        """
        # CRITICAL: If translated_segments is provided, ignore translated_text completely
        # translated_text contains the full document translation and should NEVER be used
        # for individual segments - each segment must have its own translation
        if translated_segments:
            translated_text = None
        
        if output_path is None:
            if source_file:
                base_name = source_file.stem
            else:
                from datetime import datetime
                base_name = f"subtitle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            output_path = Config.EXPORTS_DIR / "subtitles" / f"{base_name}.srt"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get segments or paragraphs - ALWAYS use original segments from transcription_data
        # Never use translated_segments as the base items - they're only for matching translations
        if use_paragraphs:
            items = transcription_data.get('paragraphs', [])
            if not items:
                # Fallback to segments if paragraphs not available
                items = transcription_data.get('segments', [])
        else:
            items = transcription_data.get('segments', [])
        
        if not items:
            raise TranscriptionError("No segments or paragraphs found in transcription data")
        
        # Generate SRT content
        srt_lines = []
        subtitle_index = 1
        
        # Get original segments/paragraphs for dual-language support
        # CRITICAL: Always use original segments from transcription_data, not translated_segments
        original_items = items
        translated_items = translated_segments if translated_segments else []
        
        # Create mapping of original to translated items by timestamp
        # Use tolerance-based matching to handle floating point precision issues
        translated_map = {}
        if translated_items:
            for t_item in translated_items:
                start = t_item.get('start', 0.0)
                # Use timestamp as key (with rounding to handle precision issues)
                key = round(start, 3)  # Round to 3 decimal places (millisecond precision)
                translated_map[key] = t_item
                # Also try with 2 decimal places as fallback
                key2 = round(start, 2)
                if key2 not in translated_map:
                    translated_map[key2] = t_item
        
        for item in original_items:
            # Get start and end times
            start_time = item.get('start', 0.0)
            end_time = item.get('end', start_time + 2.0)  # Default 2 seconds if end missing
            
            # Get original text
            original_text = item.get('text', '')
            
            # Get translated text if available - use rounded timestamp for matching
            start_key = round(start_time, 3)  # Round to 3 decimal places for matching
            translated_item = translated_map.get(start_key)
            
            # If not found with 3 decimals, try 2 decimals
            if not translated_item:
                start_key = round(start_time, 2)
                translated_item = translated_map.get(start_key)
            
            # If still not found, try exact match (for cases where timestamps are exact)
            if not translated_item and start_time in translated_map:
                translated_item = translated_map[start_time]
            
            translated_text_item = translated_item.get('text', '') if translated_item else None
            
            # Debug logging for first few segments
            if subtitle_index <= 3:
                print(f"   Subtitle {subtitle_index}: start={start_time}, matched={translated_item is not None}, "
                      f"translated_length={len(translated_text_item) if translated_text_item else 0}")
            
            # CRITICAL: Never use full translated_text for subtitle segments
            # Each segment must have its own translation from translated_segments
            # If no match found, use original text only - NEVER fallback to full translated_text
            if not translated_text_item or not translated_text_item.strip():
                # No translation for this specific segment - use original only
                # DO NOT use translated_text parameter - it contains the full document translation
                translated_text_item = None
            
            # Build subtitle text: include both original and translated if available
            if translated_text_item and translated_text_item.strip():
                # Dual-language subtitle: Original / Translated
                text = f"{original_text}\n{translated_text_item}"
            else:
                # Original only (no translation for this specific segment)
                text = original_text
            
            if not text.strip():
                continue
            
            # Clean text
            text = SubtitleGenerator._clean_text_for_subtitle(text)
            
            # Format timestamps
            start_str = SubtitleGenerator._format_srt_timestamp(start_time)
            end_str = SubtitleGenerator._format_srt_timestamp(end_time)
            
            # Write SRT entry
            srt_lines.append(str(subtitle_index))
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(text)
            srt_lines.append("")  # Empty line between subtitles
            
            subtitle_index += 1
        
        # Write to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(srt_lines))
            
            return output_path
        except Exception as e:
            raise TranscriptionError(f"Failed to generate SRT file: {str(e)}")
    
    @staticmethod
    def generate_vtt(
        transcription_data: Dict,
        output_path: Optional[Path] = None,
        source_file: Optional[Path] = None,
        use_paragraphs: bool = False,
        translated_text: Optional[str] = None,
        translated_segments: Optional[List[Dict]] = None
    ) -> Path:
        """
        Generate VTT subtitle file from transcription
        
        Args:
            transcription_data: Transcription result dictionary with 'segments' or 'paragraphs'
            output_path: Optional output file path
            source_file: Original source file (for naming)
            use_paragraphs: Use paragraph-level segmentation instead of segments
            translated_text: Optional translated text (IGNORED if translated_segments is provided)
            translated_segments: Optional translated segments with timestamps (PREFERRED)
            
        Returns:
            Path to generated VTT file
        """
        # CRITICAL: If translated_segments is provided, ignore translated_text completely
        # translated_text contains the full document translation and should NEVER be used
        # for individual segments - each segment must have its own translation
        if translated_segments:
            translated_text = None
        
        if output_path is None:
            if source_file:
                base_name = source_file.stem
            else:
                from datetime import datetime
                base_name = f"subtitle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            output_path = Config.EXPORTS_DIR / "subtitles" / f"{base_name}.vtt"
        
        # Ensure directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get segments or paragraphs - ALWAYS use original segments from transcription_data
        # Never use translated_segments as the base items - they're only for matching translations
        if use_paragraphs:
            items = transcription_data.get('paragraphs', [])
            if not items:
                # Fallback to segments if paragraphs not available
                items = transcription_data.get('segments', [])
        else:
            items = transcription_data.get('segments', [])
        
        if not items:
            raise TranscriptionError("No segments or paragraphs found in transcription data")
        
        # Generate VTT content
        vtt_lines = ["WEBVTT", ""]  # VTT header
        
        # Get original segments/paragraphs for dual-language support
        # CRITICAL: Always use original segments from transcription_data, not translated_segments
        original_items = items
        translated_items = translated_segments if translated_segments else []
        
        # Create mapping of original to translated items by timestamp
        # Use tolerance-based matching to handle floating point precision issues
        translated_map = {}
        if translated_items:
            for t_item in translated_items:
                start = t_item.get('start', 0.0)
                # Use timestamp as key (with rounding to handle precision issues)
                key = round(start, 3)  # Round to 3 decimal places (millisecond precision)
                translated_map[key] = t_item
                # Also try with 2 decimal places as fallback
                key2 = round(start, 2)
                if key2 not in translated_map:
                    translated_map[key2] = t_item
        
        vtt_entry_index = 0
        for item in original_items:
            vtt_entry_index += 1
            # Get start and end times
            start_time = item.get('start', 0.0)
            end_time = item.get('end', start_time + 2.0)  # Default 2 seconds if end missing
            
            # Get original text
            original_text = item.get('text', '')
            
            # Get translated text if available - use rounded timestamp for matching
            start_key = round(start_time, 3)  # Round to 3 decimal places for matching
            translated_item = translated_map.get(start_key)
            
            # If not found with 3 decimals, try 2 decimals
            if not translated_item:
                start_key = round(start_time, 2)
                translated_item = translated_map.get(start_key)
            
            # If still not found, try exact match (for cases where timestamps are exact)
            if not translated_item and start_time in translated_map:
                translated_item = translated_map[start_time]
            
            translated_text_item = translated_item.get('text', '') if translated_item else None
            
            # Debug logging for first few entries
            if vtt_entry_index <= 3:
                print(f"   VTT Entry {vtt_entry_index}: start={start_time}, matched={translated_item is not None}, "
                      f"translated_length={len(translated_text_item) if translated_text_item else 0}")
            
            # CRITICAL: Never use full translated_text for subtitle segments
            # Each segment must have its own translation from translated_segments
            # If no match found, use original text only - NEVER fallback to full translated_text
            if not translated_text_item or not translated_text_item.strip():
                # No translation for this specific segment - use original only
                # DO NOT use translated_text parameter - it contains the full document translation
                translated_text_item = None
            
            # Build subtitle text: include both original and translated if available
            if translated_text_item and translated_text_item.strip():
                # Dual-language subtitle: Original / Translated
                text = f"{original_text}\n{translated_text_item}"
            else:
                # Original only (no translation for this specific segment)
                text = original_text
            
            if not text.strip():
                continue
            
            # Clean text
            text = SubtitleGenerator._clean_text_for_subtitle(text)
            
            # Format timestamps
            start_str = SubtitleGenerator._format_vtt_timestamp(start_time)
            end_str = SubtitleGenerator._format_vtt_timestamp(end_time)
            
            # Write VTT entry
            vtt_lines.append(f"{start_str} --> {end_str}")
            vtt_lines.append(text)
            vtt_lines.append("")  # Empty line between subtitles
        
        # Write to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(vtt_lines))
            
            return output_path
        except Exception as e:
            raise TranscriptionError(f"Failed to generate VTT file: {str(e)}")
    
    @staticmethod
    def generate_both(
        transcription_data: Dict,
        base_name: Optional[str] = None,
        source_file: Optional[Path] = None,
        use_paragraphs: bool = False,
        translated_text: Optional[str] = None,
        translated_segments: Optional[List[Dict]] = None
    ) -> Dict[str, Path]:
        """
        Generate both SRT and VTT files
        
        Args:
            transcription_data: Transcription result dictionary
            base_name: Base name for output files (without extension)
            source_file: Original source file (for naming)
            use_paragraphs: Use paragraph-level segmentation
            translated_text: Optional translated text (IGNORED if translated_segments is provided)
            translated_segments: Optional translated segments (PREFERRED)
            
        Returns:
            Dictionary with 'srt' and 'vtt' keys pointing to file paths
        """
        # CRITICAL: If translated_segments is provided, ignore translated_text completely
        if translated_segments:
            translated_text = None
        
        if base_name is None:
            if source_file:
                base_name = source_file.stem
            else:
                from datetime import datetime
                base_name = f"subtitle_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        srt_path = Config.EXPORTS_DIR / "subtitles" / f"{base_name}.srt"
        vtt_path = Config.EXPORTS_DIR / "subtitles" / f"{base_name}.vtt"
        
        srt_file = SubtitleGenerator.generate_srt(
            transcription_data,
            output_path=srt_path,
            source_file=source_file,
            use_paragraphs=use_paragraphs,
            translated_text=translated_text,
            translated_segments=translated_segments
        )
        
        vtt_file = SubtitleGenerator.generate_vtt(
            transcription_data,
            output_path=vtt_path,
            source_file=source_file,
            use_paragraphs=use_paragraphs,
            translated_text=translated_text,
            translated_segments=translated_segments
        )
        
        return {
            'srt': srt_file,
            'vtt': vtt_file
        }
