"""
Example usage of Robust Translator for code-mixed multilingual speech
Demonstrates the improved translation pipeline
"""
from src.translation.robust_integration import RobustTranscriptionTranslationIntegration


def example_hindi_to_english():
    """Example: Translate Hindi code-mixed speech to English"""
    
    # Sample transcription with code-mixed Hindi (Hinglish)
    transcription_result = {
        'text': """Brother, how much time will it take to reach the south? Anna first coconut drink water na ji baivi south aagaya baivi how do you know? The white coconut water is yellow which means it is on its south side.""",
        'language': 'hi'  # Source language: Hindi
    }
    
    print("=" * 80)
    print("ROBUST TRANSLATION EXAMPLE: Hindi (Code-Mixed) → English")
    print("=" * 80)
    print("\nOriginal Transcription:")
    print(transcription_result['text'])
    print("\n" + "-" * 80)
    
    # Initialize robust translator
    try:
        robust_integration = RobustTranscriptionTranslationIntegration(
            enable_normalization=True,
            enable_llm_refinement=False  # Set to True if you have LLM setup
        )
        
        # Translate using robust pipeline
        print("\nTranslating with robust pipeline (sentence-by-sentence)...")
        result = robust_integration.translate_transcription(
            transcription_result=transcription_result,
            target_language='en',
            use_sentence_by_sentence=True,
            use_two_step=False
        )
        
        print("\n" + "=" * 80)
        print("TRANSLATION RESULT")
        print("=" * 80)
        print(f"\nTranslated Text:")
        print(result['translated_text'])
        
        print(f"\n\nMetadata:")
        print(f"  - Normalized: {result.get('normalized', False)}")
        print(f"  - Sentence Count: {result.get('sentence_count', 0)}")
        print(f"  - Provider: {result.get('provider', 'unknown')}")
        print(f"  - Used Preferred Provider: {result.get('used_preferred_provider', True)}")
        if result.get('fallback_provider'):
            print(f"  - Fallback Provider: {result.get('fallback_provider')}")
        
        if result.get('normalized_text'):
            print(f"\n\nNormalized Text (before translation):")
            print(result['normalized_text'])
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


def example_telugu_to_english():
    """Example: Translate Telugu code-mixed speech to English"""
    
    transcription_result = {
        'text': """Anna, eppudu vellali? First water tagali ra. Ippudu ready ga undhi.""",
        'language': 'te'  # Source language: Telugu
    }
    
    print("\n\n" + "=" * 80)
    print("ROBUST TRANSLATION EXAMPLE: Telugu (Code-Mixed) → English")
    print("=" * 80)
    print("\nOriginal Transcription:")
    print(transcription_result['text'])
    print("\n" + "-" * 80)
    
    try:
        robust_integration = RobustTranscriptionTranslationIntegration(
            enable_normalization=True
        )
        
        result = robust_integration.translate_transcription(
            transcription_result=transcription_result,
            target_language='en',
            use_sentence_by_sentence=True
        )
        
        print("\nTranslated Text:")
        print(result['translated_text'])
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n" + "=" * 80)
    print("ROBUST TRANSLATION PIPELINE - EXAMPLE USAGE")
    print("=" * 80)
    print("\nThis example demonstrates the robust translation pipeline designed")
    print("for code-mixed multilingual speech (Hinglish, etc.)")
    print("\nFeatures:")
    print("  ✓ Text normalization (filler removal, sentence fixing)")
    print("  ✓ Sentence-by-sentence translation")
    print("  ✓ Explicit source language forcing")
    print("  ✓ Multi-provider fallback")
    print("=" * 80)
    
    # Run examples
    example_hindi_to_english()
    example_telugu_to_english()
    
    print("\n" + "=" * 80)
    print("EXAMPLES COMPLETE")
    print("=" * 80)
