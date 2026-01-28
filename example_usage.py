"""
Example usage of MemoAI transcription service
Task 1: Core Transcription Module
"""
from pathlib import Path
from src.transcription import TranscriptionService


def example_basic_transcription():
    """Example: Basic transcription"""
    print("Example 1: Basic Transcription")
    print("-" * 50)
    
    service = TranscriptionService(model_name="base")
    
    # Replace with your audio/video file path
    file_path = Path("path/to/your/audio.mp3")
    
    if not file_path.exists():
        print(f"File not found: {file_path}")
        print("Please update the file_path in the example")
        return
    
    result = service.transcribe(
        file_path=file_path,
        language=None,  # Auto-detect
        save_result=True
    )
    
    print(f"Language: {result['language']}")
    print(f"Text: {result['text'][:200]}...")
    print(f"Saved to: {result.get('saved_path')}")


def example_paragraph_transcription():
    """Example: Transcription with paragraph formatting"""
    print("\nExample 2: Paragraph Formatting")
    print("-" * 50)
    
    service = TranscriptionService(model_name="base")
    
    file_path = Path("path/to/your/video.mp4")
    
    if not file_path.exists():
        print(f"File not found: {file_path}")
        return
    
    result = service.transcribe(
        file_path=file_path,
        paragraph_format=True,
        words_per_paragraph=50
    )
    
    print(f"Total paragraphs: {len(result['paragraphs'])}")
    for i, para in enumerate(result['paragraphs'][:3], 1):
        print(f"\nParagraph {i}:")
        print(f"  Time: {para['start']:.2f}s - {para['end']:.2f}s")
        print(f"  Text: {para['text'][:100]}...")


def example_supported_formats():
    """Example: Check supported formats"""
    print("\nExample 3: Supported Formats")
    print("-" * 50)
    
    service = TranscriptionService()
    formats = service.get_supported_formats()
    
    print("Supported Video Formats:")
    for fmt in formats['video']:
        print(f"  - {fmt}")
    
    print("\nSupported Audio Formats:")
    for fmt in formats['audio']:
        print(f"  - {fmt}")


if __name__ == '__main__':
    print("MemoAI Transcription Examples")
    print("=" * 50)
    
    # Uncomment to run examples
    # example_basic_transcription()
    # example_paragraph_transcription()
    example_supported_formats()
