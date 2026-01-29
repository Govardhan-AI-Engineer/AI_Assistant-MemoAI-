"""
Main entry point for MemoAI transcription
Task 1 & 2: Core Transcription + Online Media Transcription
"""
import argparse
from pathlib import Path
from src.transcription import TranscriptionService
from src.transcription.url_handler import URLHandler
from src.transcription.subtitle_parser import SubtitleParser
from src.core.config import Config


def main():
    """Main CLI interface for transcription"""
    parser = argparse.ArgumentParser(
        description='MemoAI - Transcribe audio/video files, URLs, or parse subtitle files'
    )
    
    parser.add_argument(
        'input_file',
        type=str,
        help='Path to audio/video file, YouTube/podcast URL, or subtitle file (SRT/VTT)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default=Config.WHISPER_MODEL,
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model to use (default: medium). For Telugu use "large", for other Indian languages use "medium" for strong transcription'
    )
    
    parser.add_argument(
        '--language',
        type=str,
        default=None,
        help='Language code (e.g., en, es, fr, ko). Auto-detect if not specified'
    )
    
    parser.add_argument(
        '--temperature',
        type=float,
        default=Config.WHISPER_TEMPERATURE,
        help='Temperature for transcription (0 = deterministic, higher = more variation). Default: 0'
    )
    
    parser.add_argument(
        '--paragraphs',
        action='store_true',
        help='Format output into paragraphs'
    )
    
    parser.add_argument(
        '--words-per-paragraph',
        type=int,
        default=Config.PARAGRAPH_WORD_COUNT,
        help=f'Words per paragraph (default: {Config.PARAGRAPH_WORD_COUNT})'
    )
    
    parser.add_argument(
        '--no-save',
        action='store_true',
        help='Do not save transcription to file'
    )
    
    args = parser.parse_args()
    
    # Check if input is URL, subtitle file, or regular file
    url_handler = URLHandler()
    subtitle_parser = SubtitleParser()
    input_str = args.input_file
    
    is_url = url_handler.is_url(input_str)
    is_subtitle = False
    input_path = None
    
    if not is_url:
        input_path = Path(input_str)
        is_subtitle = subtitle_parser.is_subtitle_file(input_path)
        
        # For regular files, check if they exist
        if not is_subtitle and not input_path.exists():
            print(f"Error: File not found: {input_path}")
            return 1
    
    # Auto-upgrade model based on language for STRONG transcription quality
    # Default to medium model for best accuracy across all languages
    model_to_use = args.model
    
    if args.model in ['tiny', 'base', 'small']:
        if args.language == 'te':
            # Telugu requires large model - smaller models cause high compression ratio
            model_to_use = 'large'
            print(f"⚠️  Note: Telugu language detected - Auto-upgrading to 'large' model")
            print(f"   (Large model ensures correct Telugu script without repetition)")
        elif args.language in ['hi', 'ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa', 'or', 'as']:
            # Indian languages benefit from medium model for strong transcription
            model_to_use = 'medium'
            print(f"⚠️  Note: {args.language.upper()} language detected - Auto-upgrading to 'medium' model")
            print(f"   (Medium model ensures strong transcription quality)")
        else:
            # For other languages, use medium for best accuracy
            model_to_use = 'medium'
            if args.language:
                print(f"⚠️  Note: Auto-upgrading to 'medium' model for strong transcription")
                print(f"   (Medium model ensures accurate transcription for all languages)")
            else:
                print(f"⚠️  Note: Auto-upgrading to 'medium' model for strong transcription")
                print(f"   (Medium model ensures accurate transcription for all languages)")
    elif args.model == 'medium' and args.language == 'te':
        # Telugu always needs large model
        model_to_use = 'large'
        print(f"⚠️  Note: Telugu language detected - Auto-upgrading to 'large' model")
        print(f"   (Large model ensures correct Telugu script without repetition)")
    
    # Initialize service
    print(f"Initializing transcription service with model: {model_to_use}")
    service = TranscriptionService(model_name=model_to_use)
    
    # Check supported formats (only for regular files)
    if not is_url and not is_subtitle:
        supported = service.get_supported_formats()
        file_ext = input_path.suffix.lower()
        if file_ext not in supported['video'] + supported['audio']:
            print(f"Warning: File format {file_ext} may not be supported")
            print(f"Supported formats: {supported['video'] + supported['audio']}")
    
    # Perform transcription/parsing
    try:
        if is_url:
            print(f"\nProcessing URL: {input_str}")
            is_valid, url_type = url_handler.validate_url(input_str)
            if not is_valid:
                print(f"Error: Invalid URL: {input_str}")
                return 1
            print(f"URL type: {url_type}")
            if not args.language:
                print("Auto-detecting language...")
        elif is_subtitle:
            print(f"\nParsing subtitle file: {input_path}")
            print("Note: Subtitle files are parsed directly (no transcription needed)")
            print("Use this for translation-only workflow")
        else:
            print(f"\nTranscribing: {input_path}")
            if not args.language:
                print("Auto-detecting language...")
        print("-" * 50)
        
        # Use input_str for URLs, input_path for files
        input_source = input_str if is_url else input_path
        
        result = service.transcribe(
            file_path=input_source,
            language=args.language,  # None = auto-detect
            save_result=not args.no_save,
            paragraph_format=args.paragraphs,
            words_per_paragraph=args.words_per_paragraph,
            temperature=args.temperature
        )
        
        # Display results
        if is_subtitle:
            print(f"\n✓ Subtitle parsing completed!")
            metadata = result.get('metadata', {})
            print(f"  Format: {metadata.get('format', 'unknown')}")
            print(f"  Segments: {metadata.get('segment_count', 0)}")
        else:
            detected_lang = result.get('language', 'unknown')
            print(f"\n✓ Transcription completed!")
            if not args.language:
                print(f"  Language auto-detected: {detected_lang}")
            else:
                print(f"  Language: {detected_lang}")
            
            # Show URL metadata if available
            url_metadata = result.get('metadata', {})
            if 'source' in url_metadata:
                print(f"  Source: {url_metadata.get('source', 'unknown')}")
                if 'title' in url_metadata:
                    print(f"  Title: {url_metadata.get('title', 'Unknown')}")
        
        print(f"  Text length: {len(result['text'])} characters")
        
        if args.paragraphs and 'paragraphs' in result:
            print(f"  Paragraphs: {len(result['paragraphs'])}")
        
        if not args.no_save:
            print(f"\n✓ Saved to: {result.get('saved_path', 'N/A')}")
            if 'text_file_path' in result:
                print(f"✓ Text file: {result['text_file_path']}")
        
        # Display transcription preview
        print("\n" + "=" * 50)
        print("TRANSCRIPTION PREVIEW:")
        print("=" * 50)
        preview = result['text'][:500]
        print(preview)
        if len(result['text']) > 500:
            print(f"\n... ({len(result['text']) - 500} more characters)")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return 1


if __name__ == '__main__':
    exit(main())
