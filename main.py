"""
Main entry point for MemoAI transcription
Task 1: Core Transcription Module
"""
import argparse
from pathlib import Path
from src.transcription import TranscriptionService
from src.core.config import Config


def main():
    """Main CLI interface for transcription"""
    parser = argparse.ArgumentParser(
        description='MemoAI - Transcribe audio/video files'
    )
    
    parser.add_argument(
        'input_file',
        type=str,
        help='Path to audio/video file (MP4, MP3, AAC, M4A, etc.)'
    )
    
    parser.add_argument(
        '--model',
        type=str,
        default=Config.WHISPER_MODEL,
        choices=['tiny', 'base', 'small', 'medium', 'large'],
        help='Whisper model to use (default: base). For Telugu/Indian languages, use "small" or larger for better accuracy'
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
    
    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1
    
    # Auto-upgrade model based on language
    # Telugu requires medium model - small model causes repetition issues (compression_ratio > 11)
    model_to_use = args.model
    
    if args.model in ['tiny', 'base', 'small', 'medium']:
        if args.language == 'te':
            # Telugu requires large model - smaller models cause high compression ratio
            model_to_use = 'large'
            print(f"⚠️  Note: Telugu language detected - Auto-upgrading to 'large' model")
            print(f"   (Small/medium models cause repetition issues with Telugu - compression_ratio > 7)")
            print(f"   (Large model ensures correct Telugu script without repetition)")
        elif args.model in ['tiny', 'base']:
            model_to_use = 'small'  # Use small for other languages
            if args.language:
                print(f"⚠️  Note: Auto-upgrading to 'small' model for best accuracy")
                print(f"   (Small model ensures correct transcription for all languages)")
            else:
                print(f"⚠️  Note: Auto-upgrading to 'small' model for best accuracy")
                print(f"   (Small model ensures correct transcription for all languages)")
    
    # Initialize service
    print(f"Initializing transcription service with model: {model_to_use}")
    service = TranscriptionService(model_name=model_to_use)
    
    # Check supported formats
    supported = service.get_supported_formats()
    file_ext = input_path.suffix.lower()
    if file_ext not in supported['video'] + supported['audio']:
        print(f"Warning: File format {file_ext} may not be supported")
        print(f"Supported formats: {supported['video'] + supported['audio']}")
    
    # Perform transcription
    try:
        print(f"\nTranscribing: {input_path}")
        if not args.language:
            print("Auto-detecting language...")
        print("-" * 50)
        
        result = service.transcribe(
            file_path=input_path,
            language=args.language,  # None = auto-detect
            save_result=not args.no_save,
            paragraph_format=args.paragraphs,
            words_per_paragraph=args.words_per_paragraph,
            temperature=args.temperature
        )
        
        # Display results
        detected_lang = result.get('language', 'unknown')
        print(f"\n✓ Transcription completed!")
        if not args.language:
            print(f"  Language auto-detected: {detected_lang}")
        else:
            print(f"  Language: {detected_lang}")
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
