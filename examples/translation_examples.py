"""
Translation Module - Example Usage

This file demonstrates how to use the translation module with:
- Paragraph-level translation
- Line-by-line translation
- Fallback mechanism
- Re-translation for quality refinement
"""
from src.translation import TranslationService, TranslationGranularity


def example_paragraph_translation():
    """Example: Paragraph-level translation"""
    print("=" * 70)
    print("Example 1: Paragraph-Level Translation")
    print("=" * 70)
    
    # Initialize service
    service = TranslationService(
        provider_priority=['google', 'libre', 'deepl'],
        enable_retranslation=True
    )
    
    # Sample text (Telugu)
    text = """
    ఈ వ్యవస్థ మల్టీ-ప్రొవైడర్ అనువాదాన్ని మద్దతు చేస్తుంది.
    ఇది స్వయంచాలక ఫాల్బ్యాక్ మెకానిజంను కలిగి ఉంది.
    అనువాద నాణ్యతను మెరుగుపరచడానికి రీ-ట్రాన్స్లేషన్ సామర్థ్యం కూడా ఉంది.
    """
    
    # Translate to English
    result = service.translate(
        text=text,
        target_language='en',
        source_language='te',  # Telugu
        granularity=TranslationGranularity.PARAGRAPH,
        preferred_provider='google'
    )
    
    print(f"\nOriginal (Telugu):\n{text}")
    print(f"\nTranslated (English):\n{result['text']}")
    print(f"\nProvider used: {result['provider']}")
    if result['secondary_provider']:
        print(f"Re-translated with: {result['secondary_provider']}")
    print(f"Granularity: {result['granularity']}")


def example_line_by_line_translation():
    """Example: Line-by-line translation (for subtitles)"""
    print("\n" + "=" * 70)
    print("Example 2: Line-by-Line Translation (for Subtitles)")
    print("=" * 70)
    
    service = TranslationService()
    
    # Sample subtitle text (Hindi)
    text = """
    नमस्ते, यह एक उदाहरण है।
    यह प्रणाली बहु-प्रदाता अनुवाद का समर्थन करती है।
    यह स्वचालित फॉलबैक तंत्र है।
    """
    
    # Translate line by line
    result = service.translate(
        text=text,
        target_language='en',
        source_language='hi',  # Hindi
        granularity=TranslationGranularity.LINE_BY_LINE,
        preferred_provider='google'
    )
    
    print(f"\nOriginal (Hindi):\n{text}")
    print(f"\nTranslated (English):\n{result['text']}")
    print(f"\nProvider: {result['provider']}")
    print(f"Granularity: {result['granularity']}")


def example_fallback_mechanism():
    """Example: Fallback mechanism when provider fails"""
    print("\n" + "=" * 70)
    print("Example 3: Fallback Mechanism")
    print("=" * 70)
    
    # Initialize with specific priority
    service = TranslationService(
        provider_priority=['deepl', 'google', 'libre']  # Try DeepL first
    )
    
    text = "Hello, this is a test."
    
    # Try to translate (will fallback if DeepL unavailable)
    try:
        result = service.translate(
            text=text,
            target_language='es',  # Spanish
            source_language='en',
            preferred_provider='deepl'  # Prefer DeepL
        )
        
        print(f"\nOriginal: {text}")
        print(f"Translated: {result['text']}")
        print(f"Provider used: {result['provider']}")
        print(f"\nNote: If DeepL unavailable, automatically fell back to next provider")
        
    except Exception as e:
        print(f"\nError: {e}")


def example_retranslation():
    """Example: Re-translation for quality refinement"""
    print("\n" + "=" * 70)
    print("Example 4: Re-translation for Quality Refinement")
    print("=" * 70)
    
    service = TranslationService(
        enable_retranslation=True
    )
    
    text = "This is a complex sentence that may benefit from re-translation."
    
    # Translate with re-translation enabled
    result = service.translate(
        text=text,
        target_language='fr',  # French
        source_language='en',
        enable_retranslation=True
    )
    
    print(f"\nOriginal: {text}")
    print(f"Translated: {result['text']}")
    print(f"Primary provider: {result['provider']}")
    if result['secondary_provider']:
        print(f"Re-translated with: {result['secondary_provider']}")
        print("(Re-translation can help refine translation quality)")


def example_batch_translation():
    """Example: Batch translation of paragraphs"""
    print("\n" + "=" * 70)
    print("Example 5: Batch Translation of Paragraphs")
    print("=" * 70)
    
    service = TranslationService()
    
    # Multiple paragraphs
    paragraphs = [
        "First paragraph to translate.",
        "Second paragraph with different content.",
        "Third paragraph for batch processing."
    ]
    
    # Translate all paragraphs
    translated = service.translate_paragraphs(
        paragraphs=paragraphs,
        target_language='de',  # German
        source_language='en'
    )
    
    print("\nOriginal paragraphs:")
    for i, para in enumerate(paragraphs, 1):
        print(f"{i}. {para}")
    
    print("\nTranslated paragraphs:")
    for i, para in enumerate(translated, 1):
        print(f"{i}. {para}")


def example_provider_info():
    """Example: Get provider information"""
    print("\n" + "=" * 70)
    print("Example 6: Provider Information")
    print("=" * 70)
    
    service = TranslationService()
    
    # Get available providers
    available = service.get_available_providers()
    print(f"\nAvailable providers: {available}")
    
    # Get provider info
    info = service.get_provider_info()
    print("\nProvider details:")
    for name, details in info.items():
        status = "✅ Available" if details['available'] else "❌ Unavailable"
        priority = " (Priority)" if details['priority'] else ""
        print(f"  {name}: {status}{priority}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("Translation Module - Usage Examples")
    print("=" * 70)
    
    try:
        # Run examples
        example_paragraph_translation()
        example_line_by_line_translation()
        example_fallback_mechanism()
        example_retranslation()
        example_batch_translation()
        example_provider_info()
        
        print("\n" + "=" * 70)
        print("All examples completed!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()
