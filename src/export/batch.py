"""
Batch export orchestration module
Task 4: Export & Output
"""
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
from src.core.config import Config
from src.core.exceptions import TranscriptionError
from src.export.subtitles import SubtitleGenerator
from src.export.documents import DocumentExporter
from src.export.tts import TTSSynthesizer


class BatchExporter:
    """Orchestrate batch export of multiple transcripts"""
    
    def __init__(self, tts_engine: str = "gtts"):
        """
        Initialize batch exporter
        
        Args:
            tts_engine: TTS engine to use ('gtts' or 'pyttsx3')
        """
        self.tts_engine = tts_engine
        self.subtitle_gen = SubtitleGenerator
        self.doc_exporter = DocumentExporter
        self.tts_synthesizer = None
        
        # Initialize TTS if needed (lazy initialization)
        try:
            self.tts_synthesizer = TTSSynthesizer(tts_engine=tts_engine)
        except TranscriptionError:
            # TTS not available, but that's okay for batch export
            pass
    
    def export_transcription(
        self,
        transcription_data: Dict,
        source_file: Optional[Path] = None,
        base_name: Optional[str] = None,
        formats: Optional[Set[str]] = None,
        translated_text: Optional[str] = None,
        translated_paragraphs: Optional[List[Dict]] = None,
        translated_segments: Optional[List[Dict]] = None,
        tts_language: Optional[str] = None,
        tts_per_paragraph: bool = False,
        include_timestamps: bool = True
    ) -> Dict[str, Path]:
        """
        Export a single transcription in multiple formats
        
        Args:
            transcription_data: Transcription result dictionary
            source_file: Original source file (for naming)
            base_name: Base name for output files
            formats: Set of formats to export ('srt', 'vtt', 'md', 'txt', 'json', 'tts')
            translated_text: Optional translated text
            translated_paragraphs: Optional translated paragraphs
            translated_segments: Optional translated segments
            tts_language: Language code for TTS (required if 'tts' in formats)
            tts_per_paragraph: Create one TTS file per paragraph
            include_timestamps: Include timestamps in documents
            
        Returns:
            Dictionary mapping format names to file paths
        """
        if formats is None:
            formats = {'srt', 'vtt', 'md', 'txt', 'json'}
        
        if base_name is None:
            if source_file:
                base_name = source_file.stem
            else:
                base_name = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        exported_files = {}
        
        # Export subtitles
        if 'srt' in formats or 'vtt' in formats:
            subtitle_formats = []
            if 'srt' in formats:
                subtitle_formats.append('srt')
            if 'vtt' in formats:
                subtitle_formats.append('vtt')
            
            if len(subtitle_formats) == 2:
                # Generate both
                subtitle_files = self.subtitle_gen.generate_both(
                    transcription_data,
                    base_name=base_name,
                    source_file=source_file,
                    use_paragraphs=False,
                    translated_text=translated_text,
                    translated_segments=translated_segments
                )
                exported_files.update(subtitle_files)
            elif 'srt' in subtitle_formats:
                srt_path = Config.EXPORTS_DIR / "subtitles" / f"{base_name}.srt"
                exported_files['srt'] = self.subtitle_gen.generate_srt(
                    transcription_data,
                    output_path=srt_path,
                    source_file=source_file,
                    translated_text=translated_text,
                    translated_segments=translated_segments
                )
            elif 'vtt' in subtitle_formats:
                vtt_path = Config.EXPORTS_DIR / "subtitles" / f"{base_name}.vtt"
                exported_files['vtt'] = self.subtitle_gen.generate_vtt(
                    transcription_data,
                    output_path=vtt_path,
                    source_file=source_file,
                    translated_text=translated_text,
                    translated_segments=translated_segments
                )
        
        # Export documents
        if 'md' in formats or 'txt' in formats or 'json' in formats:
            doc_formats = []
            if 'md' in formats:
                doc_formats.append('md')
            if 'txt' in formats:
                doc_formats.append('txt')
            if 'json' in formats:
                doc_formats.append('json')
            
            if len(doc_formats) == 3:
                # Generate all document formats
                doc_files = self.doc_exporter.export_all(
                    transcription_data,
                    base_name=base_name,
                    source_file=source_file,
                    translated_text=translated_text,
                    translated_paragraphs=translated_paragraphs,
                    translated_segments=translated_segments,
                    include_timestamps=include_timestamps
                )
                exported_files.update(doc_files)
            else:
                # Generate individual formats
                if 'md' in doc_formats:
                    md_path = Config.EXPORTS_DIR / "documents" / f"{base_name}.md"
                    exported_files['md'] = self.doc_exporter.export_markdown(
                        transcription_data,
                        output_path=md_path,
                        source_file=source_file,
                        translated_text=translated_text,
                        translated_paragraphs=translated_paragraphs,
                        include_timestamps=include_timestamps
                    )
                if 'txt' in doc_formats:
                    txt_path = Config.EXPORTS_DIR / "documents" / f"{base_name}.txt"
                    exported_files['txt'] = self.doc_exporter.export_text(
                        transcription_data,
                        output_path=txt_path,
                        source_file=source_file,
                        translated_text=translated_text,
                        translated_paragraphs=translated_paragraphs,
                        include_timestamps=include_timestamps
                    )
                if 'json' in doc_formats:
                    json_path = Config.EXPORTS_DIR / "documents" / f"{base_name}.json"
                    exported_files['json'] = self.doc_exporter.export_json(
                        transcription_data,
                        output_path=json_path,
                        source_file=source_file,
                        translated_text=translated_text,
                        translated_paragraphs=translated_paragraphs,
                        translated_segments=translated_segments
                    )
        
        # Export TTS
        if 'tts' in formats:
            if not self.tts_synthesizer:
                raise TranscriptionError("TTS not available. Install gTTS or pyttsx3.")
            
            if not tts_language:
                # Try to get language from transcription or translation
                tts_language = transcription_data.get('language', 'en')
                if translated_text:
                    # Assume translation language (this is a simplification)
                    # In a real scenario, you'd track the target language
                    tts_language = 'en'  # Default to English for translations
            
            tts_files = self.tts_synthesizer.synthesize_transcription(
                transcription_data,
                language=tts_language,
                base_name=base_name,
                source_file=source_file,
                translated_text=translated_text,
                translated_paragraphs=translated_paragraphs,
                output_format="mp3",
                per_paragraph=tts_per_paragraph
            )
            
            if len(tts_files) == 1:
                exported_files['tts'] = tts_files[0]
            else:
                # Multiple TTS files (per paragraph)
                for idx, tts_file in enumerate(tts_files):
                    exported_files[f'tts_para_{idx+1}'] = tts_file
        
        return exported_files
    
    def export_multiple(
        self,
        transcriptions: List[Dict],
        base_names: Optional[List[str]] = None,
        source_files: Optional[List[Path]] = None,
        formats: Optional[Set[str]] = None,
        translated_texts: Optional[List[str]] = None,
        translated_paragraphs_list: Optional[List[List[Dict]]] = None,
        tts_language: Optional[str] = None,
        tts_per_paragraph: bool = False
    ) -> List[Dict[str, Path]]:
        """
        Export multiple transcriptions in batch
        
        Args:
            transcriptions: List of transcription result dictionaries
            base_names: Optional list of base names (one per transcription)
            source_files: Optional list of source files (one per transcription)
            formats: Set of formats to export
            translated_texts: Optional list of translated texts (one per transcription)
            translated_paragraphs_list: Optional list of translated paragraph lists
            tts_language: Language code for TTS
            tts_per_paragraph: Create one TTS file per paragraph
            
        Returns:
            List of dictionaries, each mapping format names to file paths
        """
        if formats is None:
            formats = {'srt', 'vtt', 'md', 'txt', 'json'}
        
        if base_names is None:
            base_names = [None] * len(transcriptions)
        
        if source_files is None:
            source_files = [None] * len(transcriptions)
        
        if translated_texts is None:
            translated_texts = [None] * len(transcriptions)
        
        if translated_paragraphs_list is None:
            translated_paragraphs_list = [None] * len(transcriptions)
        
        # Ensure all lists have same length
        num_transcriptions = len(transcriptions)
        if len(base_names) < num_transcriptions:
            base_names.extend([None] * (num_transcriptions - len(base_names)))
        if len(source_files) < num_transcriptions:
            source_files.extend([None] * (num_transcriptions - len(source_files)))
        if len(translated_texts) < num_transcriptions:
            translated_texts.extend([None] * (num_transcriptions - len(translated_texts)))
        if len(translated_paragraphs_list) < num_transcriptions:
            translated_paragraphs_list.extend([None] * (num_transcriptions - len(translated_paragraphs_list)))
        
        exported_batch = []
        
        for idx, transcription in enumerate(transcriptions):
            try:
                exported_files = self.export_transcription(
                    transcription_data=transcription,
                    source_file=source_files[idx],
                    base_name=base_names[idx],
                    formats=formats,
                    translated_text=translated_texts[idx],
                    translated_paragraphs=translated_paragraphs_list[idx],
                    tts_language=tts_language,
                    tts_per_paragraph=tts_per_paragraph
                )
                exported_batch.append(exported_files)
            except Exception as e:
                print(f"WARNING: Failed to export transcription {idx+1}: {e}")
                exported_batch.append({})
        
        return exported_batch
    
    @staticmethod
    def setup_export_directories():
        """Create export directory structure"""
        directories = [
            Config.EXPORTS_DIR / "subtitles",
            Config.EXPORTS_DIR / "documents",
            Config.EXPORTS_DIR / "audio"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
        
        return directories
