"""
Answer Refinement using LLM
Generates high-quality answers from retrieved chunks
"""
from typing import List, Dict, Any, Optional

try:
    from groq import Groq
    import os
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class AnswerRefiner:
    """
    Refines answers using LLM to generate coherent, well-structured responses
    Universal language support for all languages
    """
    
    # Language names mapping
    LANGUAGE_NAMES = {
        'en': 'English', 'hi': 'Hindi', 'te': 'Telugu', 'ta': 'Tamil',
        'kn': 'Kannada', 'ml': 'Malayalam', 'gu': 'Gujarati', 'pa': 'Punjabi',
        'bn': 'Bengali', 'mr': 'Marathi', 'or': 'Odia', 'as': 'Assamese',
        'de': 'German', 'fr': 'French', 'es': 'Spanish', 'it': 'Italian',
        'pt': 'Portuguese', 'nl': 'Dutch', 'ru': 'Russian', 'pl': 'Polish',
        'uk': 'Ukrainian', 'zh': 'Chinese', 'ja': 'Japanese', 'ko': 'Korean',
        'ar': 'Arabic', 'th': 'Thai', 'vi': 'Vietnamese', 'tr': 'Turkish',
        'he': 'Hebrew', 'cs': 'Czech', 'sv': 'Swedish', 'no': 'Norwegian',
        'fi': 'Finnish', 'da': 'Danish', 'el': 'Greek', 'hu': 'Hungarian',
        'ro': 'Romanian', 'bg': 'Bulgarian', 'hr': 'Croatian', 'sk': 'Slovak',
        'sl': 'Slovenian', 'sr': 'Serbian'
    }
    
    def __init__(self, use_llm: bool = True, embedder=None):
        """
        Initialize answer refiner
        
        Args:
            use_llm: Use LLM for refinement (default: True)
            embedder: Optional MultilingualEmbedder for semantic similarity checks
        """
        self.use_llm = use_llm and GROQ_AVAILABLE
        self.groq_client = None
        self.embedder = embedder  # Store embedder for semantic similarity checks
        
        if self.use_llm:
            try:
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    self.groq_client = Groq(api_key=api_key)
                    print("✅ Answer refiner initialized with Groq")
                else:
                    self.use_llm = False
                    print("⚠️  GROQ_API_KEY not found, using simple concatenation")
            except Exception as e:
                print(f"⚠️  Failed to initialize Groq: {e}")
                self.use_llm = False
    
    def refine_answer(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        language: str = 'en',
        max_length: int = 500,
        min_relevance: float = 0.3,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Refine answer using LLM with optional conversation history
        
        Args:
            question: User question
            retrieved_chunks: Retrieved context chunks
            language: Target language
            max_length: Maximum answer length
            min_relevance: Minimum relevance threshold for using context
            conversation_history: Optional list of previous messages in conversation
            
        Returns:
            Dictionary with:
            - 'refined_answer': Refined answer text
            - 'method': Refinement method used
            - 'chunks_used': Number of chunks used
            - 'is_from_context': Whether answer is from user's data
            - 'context_relevant': Whether context is relevant
        """
        if not retrieved_chunks:
            return {
                'refined_answer': None,  # Signal to use general knowledge
                'method': 'none',
                'chunks_used': 0,
                'is_from_context': False,
                'context_relevant': False
            }
        
        # Check if context is relevant
        context_relevant = self._check_context_relevance(question, retrieved_chunks, min_relevance)
        
        if not context_relevant:
            return {
                'refined_answer': None,  # Signal to use general knowledge
                'method': 'none',
                'chunks_used': 0,
                'is_from_context': False,
                'context_relevant': False
            }
        
        if self.use_llm and self.groq_client:
            result = self._refine_with_llm(question, retrieved_chunks, language, max_length, conversation_history)
            result['is_from_context'] = True
            result['context_relevant'] = True
            return result
        else:
            result = self._refine_simple(question, retrieved_chunks, language)
            result['is_from_context'] = True
            result['context_relevant'] = True
            return result
    
    def _check_context_relevance(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        min_relevance: float
    ) -> bool:
        """
        Check if retrieved context is relevant to the question
        Improved for multilingual support
        """
        if not retrieved_chunks:
            return False
        
        # Handle very short queries (greetings, etc.) - treat as general knowledge
        question_lower = question.lower().strip()
        short_greetings = {'hi', 'hey', 'hello', 'bye', 'thanks', 'thank you', 'ok', 'okay', 'yes', 'no',
                          'नमस्ते', 'हैलो', 'धन्यवाद', 'ठीक', 'हाँ', 'नहीं',
                          'నమస్కారం', 'హలో', 'ధన్యవాదాలు', 'సరే', 'అవును', 'కాదు'}
        
        # If it's a very short query or a greeting, don't use context
        if len(question_lower) <= 3 or question_lower in short_greetings:
            return False
        
        # Improved relevance check for multilingual content
        # For multilingual queries, we need semantic similarity, not just keyword matching
        # Since chunks are already retrieved by semantic search, if they exist, they're likely relevant
        
        # Check if we have chunks with reasonable content
        valid_chunks = [chunk for chunk in retrieved_chunks if chunk.get('text', '').strip()]
        
        if not valid_chunks:
            return False
        
        # For multilingual queries (Hindi, Telugu, etc.), semantic search already filtered
        # So if we have chunks, they're likely relevant
        # Additional check: ensure chunks have substantial content
        substantial_chunks = [chunk for chunk in valid_chunks if len(chunk.get('text', '').strip()) > 20]
        
        if len(substantial_chunks) >= 1:
            # We have at least one substantial chunk - consider relevant
            # The semantic search already did the heavy lifting
            return True
        
        # Fallback: keyword-based check for English
        import re
        question_keywords = set(re.findall(r'\b\w+\b', question.lower()))
        question_keywords = {w for w in question_keywords if len(w) > 2}  # Filter short words
        
        if not question_keywords:
            return False
        
        # Check top chunks for keyword overlap
        relevant_count = 0
        for chunk in retrieved_chunks[:3]:  # Check top 3 chunks
            chunk_text = chunk.get('text', '').lower()
            chunk_keywords = set(re.findall(r'\b\w+\b', chunk_text))
            
            overlap = len(question_keywords & chunk_keywords)
            relevance = overlap / len(question_keywords) if question_keywords else 0
            
            if relevance >= min_relevance:
                relevant_count += 1
        
        # At least one chunk should be relevant
        return relevant_count > 0
    
    def _refine_with_llm(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        language: str,
        max_length: int,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Refine answer using LLM with improved prompts and optional conversation history"""
        try:
            # CRITICAL FIX: Filter chunks FIRST before preparing context
            # This ensures irrelevant chunks are never included in the LLM context
            filtered_chunks = self._filter_irrelevant_chunks(retrieved_chunks, question=question)
            
            # Prepare context from FILTERED chunks only
            context_parts = []
            for i, chunk in enumerate(filtered_chunks[:15]):  # Use filtered chunks, not original
                text = chunk.get('text', '')
                if not text:
                    # Try alternative field names
                    text = chunk.get('content', '') or chunk.get('chunk_text', '')
                
                if text and text.strip():
                    # Use more context (up to 2000 chars) for better fact extraction
                    chunk_text = text[:2000] + "..." if len(text) > 2000 else text
                    context_parts.append(f"[Source {i+1}]: {chunk_text}")
            
            context = '\n\n'.join(context_parts) if context_parts else "No context available."
            
            # Debug: Log if context is empty
            if not context_parts:
                print(f"⚠️  WARNING: No valid text found in filtered chunks!")
                print(f"   Original chunks: {len(retrieved_chunks)}, Filtered chunks: {len(filtered_chunks)}")
                # Try simple fallback
                return self._refine_simple(question, filtered_chunks, language)
            
            # Try LangChain first if available
            try:
                from src.rag.langchain_qa import LangChainRAGQA
                langchain_qa = LangChainRAGQA(use_langchain=True)
                if langchain_qa.use_langchain:
                    answer = langchain_qa.generate_answer(question, filtered_chunks, language)
                    # Prepare context for validation from filtered chunks
                    context_parts = []
                    for chunk in filtered_chunks[:15]:
                        text = chunk.get('text', '') or chunk.get('content', '') or chunk.get('chunk_text', '')
                        if text:
                            context_parts.append(text[:2000])
                    validation_context = '\n\n'.join(context_parts) if context_parts else context
                    # Clean and validate answer
                    answer = self._clean_answer_format(answer)
                    answer = self._validate_no_hallucination(answer, validation_context)
                    # Remove sentences that don't answer the question
                    answer = self._filter_irrelevant_sentences(answer, question, validation_context)
                    # FINAL VALIDATION: Remove specific irrelevant phrases
                    answer = self._remove_irrelevant_phrases(answer, question, language)
                    return {
                        'refined_answer': answer,
                        'method': 'langchain',
                        'chunks_used': min(len(filtered_chunks), 15),
                        'is_from_context': True,
                        'context_relevant': True
                    }
            except Exception as e:
                print(f"⚠️  LangChain fallback: {e}")
                pass  # Fallback to direct LLM call
            
            # Use filtered chunks for direct LLM call (already filtered above)
            # No need to reassign - filtered_chunks is already used
            
            # Universal multilingual prompt (works for all languages)
            lang_name = self._get_language_name(language)
            
            system_prompt = f"""You are a comprehensive information extractor. Answer questions using ONLY the information provided in the context below.

CRITICAL LANGUAGE RULE:
- The question is in {lang_name} language
- You MUST answer in {lang_name} language ONLY
- Do NOT switch to any other language, even if context chunks are in a different language
- If context is in a different language, extract the meaning but answer in {lang_name}

COMPREHENSIVE EXTRACTION RULES:
1. Use ONLY information from the context - do NOT add any information not explicitly stated
2. If a fact is not in the context, do NOT mention it
3. Do NOT create contradictions - if context says one thing, don't say the opposite
4. Extract ALL relevant information - if the question asks for "changes", "impacts", "facts", or "details", include ALL of them mentioned in the context
5. Include specific numbers, dates, and facts ONLY if they are explicitly in the context
6. Write in natural, flowing prose - do NOT use bullet points, numbered lists (1., 2., 3.), or structured sections
7. Write in continuous sentences, connecting all relevant points naturally
8. Be thorough and comprehensive - include all relevant changes, impacts, or facts from the context
9. Include ALL specific numbers (e.g., "25 crore", "11 years") and dates (e.g., "26 November 2015", "2026-2027") mentioned in the context

ANTI-HALLUCINATION RULES (STRICT):
- Before mentioning ANY fact, verify it exists EXACTLY in the context
- Do NOT infer, assume, or add general knowledge
- Do NOT add facts that are "common sense" but not in context
- If context doesn't mention something, do NOT include it
- Do NOT add information about "previous prime minister", "former prime minister", "always stable", "consistently stable", "stable figure", "always present", or "always guiding" unless these EXACT phrases appear in the context
- Do NOT use phrases like "context does not provide", "I cannot find", "the context doesn't mention" - if information is not in context, simply don't mention it
- Do NOT add descriptive phrases like "consistently been", "always present", "guiding the nation" unless explicitly stated in context
- Ignore any chunks that contain sample/test content like "You are listening to a sample MP3 audio file"

CRITICAL GROUNDING RULE:
- Every sentence in your answer MUST be directly supported by the context
- If you cannot find exact support for a claim in the context, DO NOT include it
- Do NOT paraphrase or rephrase context in ways that add meaning not present in the original
- Stick to facts EXACTLY as stated in the context

CRITICAL RELEVANCE RULE:
- ONLY include information that DIRECTLY answers the question
- If a chunk in the context talks about a different topic (e.g., economy, policy, development) but uses similar words, DO NOT include it
- For example, if the question is "how to improve English", DO NOT include chunks about "improving at grassroots level" or "India improving economy" - these are NOT about improving English language skills
- Filter out any content that doesn't directly relate to the question topic
- If the question is about learning/improving a skill, ONLY include chunks about that specific skill, not general improvement in other areas

CRITICAL: Do NOT say "context does not provide" or "the context doesn't mention" - if information is missing, just omit it. Never use disclaimers.

FORMAT:
Write a clear, comprehensive, natural answer in {lang_name} that directly addresses the question. Include ALL relevant changes, facts, or details mentioned in the context, including specific numbers and dates. Write in flowing prose as continuous sentences. Do NOT use numbered lists (1., 2., 3.) or bullet points."""
            
            # Count how many chunks we're using
            num_chunks = len(filtered_chunks[:15])
            
            # Build conversation history context if available
            conversation_context = ""
            if conversation_history and len(conversation_history) > 0:
                conv_parts = []
                for msg in conversation_history[-5:]:  # Last 5 messages for context
                    if msg.get('role') == 'user':
                        conv_parts.append(f"Previous question: {msg.get('content', '')[:150]}")
                    elif msg.get('role') == 'assistant':
                        conv_parts.append(f"Previous answer: {msg.get('content', '')[:200]}")
                
                if conv_parts:
                    conversation_context = f"""
PREVIOUS CONVERSATION CONTEXT:
{chr(10).join(conv_parts)}

CURRENT QUESTION (may be a follow-up to previous questions):
"""
            
            user_prompt = f"""Question (in {lang_name}): {question}{conversation_context}

Context from transcripts (MULTIPLE SOURCES - YOU HAVE {num_chunks} CHUNKS - USE ALL OF THEM):
{context}

CRITICAL INSTRUCTION - USE ALL CHUNKS (MOST IMPORTANT):
- You have MULTIPLE context chunks above (marked as [Source 1], [Source 2], [Source 3], etc.)
- You MUST read and synthesize information from ALL chunks, not just one
- If chunk [Source 1] mentions one method/tip, and [Source 2] mentions another method/tip, include BOTH
- If chunk [Source 3] has additional details, include those too
- Synthesize and combine information from ALL chunks into a comprehensive answer
- Do NOT just use the first chunk - you must use information from ALL relevant chunks
- For "how to" questions, list ALL methods/tips/ways mentioned across ALL chunks
- If multiple chunks mention different aspects, combine them all

CRITICAL RELEVANCE FILTERING:
- BEFORE including ANY information from a context chunk, verify it DIRECTLY answers the question
- If a chunk uses similar words but is about a DIFFERENT topic, IGNORE that specific chunk completely
- Example: If question is "how to improve English" and a chunk says "programs to improve at grassroots level" or "India improving economy", DO NOT include it - it's NOT about improving English language skills
- ONLY include chunks that are about the EXACT topic asked in the question
- If the question is about learning/improving a skill (like English), ONLY include chunks about that skill, not general improvement in other areas

CRITICAL INSTRUCTION: If the question asks about "how to", "ways to", "methods to", "changes", "impacts", "developments", "what happened", or "what are described", you MUST list ALL of them mentioned across ALL context chunks. Do not summarize - extract and list every single method, tip, way, change, fact, development, or detail mentioned. Be exhaustive and comprehensive. Synthesize information from ALL chunks.

IMPORTANT: Answer in {lang_name} language ONLY. The question is in {lang_name}, so your answer must be in {lang_name}.

Provide a clear, comprehensive answer that directly addresses the question. Extract and synthesize information from ALL context chunks above that DIRECTLY answer the question. If multiple chunks mention different methods/tips/ways, include ALL of them. Filter out any chunks that use similar words but are about different topics. Use ONLY information from the context above. Do NOT add any information not explicitly stated. Write naturally in continuous prose sentences, connecting all relevant points from multiple chunks. Do NOT use numbered lists (1., 2., 3.) or bullet points. Be thorough and include all relevant information from ALL chunks. Answer in {lang_name}."""

            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,  # Low temperature for factuality, but allow comprehensive extraction
                max_tokens=min(max_length * 3, 1500),  # Increased to allow comprehensive answers
                top_p=0.9  # Slightly higher for more comprehensive responses
            )
            
            refined_answer = response.choices[0].message.content.strip()
            
            # Clean up verbose format (remove structured sections)
            refined_answer = self._clean_answer_format(refined_answer)
            
            # Validate no hallucination (check facts against context)
            refined_answer = self._validate_no_hallucination(refined_answer, context)
            
            # Additional grounding check: Verify each sentence has support in context
            refined_answer = self._verify_grounding(refined_answer, context)
            
            # NEW: Remove sentences that don't answer the question
            refined_answer = self._filter_irrelevant_sentences(refined_answer, question, context)
            
            # FINAL VALIDATION: Remove specific irrelevant phrases that shouldn't appear
            refined_answer = self._remove_irrelevant_phrases(refined_answer, question, language)
            
            return {
                'refined_answer': refined_answer,
                'method': 'llm',
                'chunks_used': min(len(filtered_chunks), 15),  # Use filtered_chunks count
                'is_from_context': True,
                'context_relevant': True
            }
            
        except Exception as e:
            print(f"⚠️  LLM refinement failed: {e}")
            return self._refine_simple(question, retrieved_chunks, language)
    
    def _refine_with_llm_streaming(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        language: str,
        max_length: int,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ):
        """Stream answer using LLM (generator function) with optional conversation history"""
        try:
            # Prepare context from top chunks
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks[:15]):
                text = chunk.get('text', '') or chunk.get('content', '') or chunk.get('chunk_text', '')
                if text and text.strip():
                    chunk_text = text[:2000] + "..." if len(text) > 2000 else text
                    context_parts.append(f"[Source {i+1}]: {chunk_text}")
            
            context = '\n\n'.join(context_parts) if context_parts else "No context available."
            
            if not context_parts:
                # Fallback: yield simple answer
                answer_parts = []
                for chunk in retrieved_chunks[:3]:
                    text = chunk.get('text', '')
                    if text:
                        answer_parts.append(text)
                answer = ' '.join(answer_parts)
                for word in answer.split():
                    yield word + ' '
                return
            
            # Filter chunks
            filtered_chunks = self._filter_irrelevant_chunks(retrieved_chunks, question=question)
            retrieved_chunks = filtered_chunks if filtered_chunks else retrieved_chunks[:5]
            
            # Build conversation history context if available
            conversation_context = ""
            if conversation_history and len(conversation_history) > 0:
                conv_parts = []
                for msg in conversation_history[-5:]:  # Last 5 messages
                    if msg.get('role') == 'user':
                        conv_parts.append(f"Previous question: {msg.get('content', '')[:150]}")
                    elif msg.get('role') == 'assistant':
                        conv_parts.append(f"Previous answer: {msg.get('content', '')[:200]}")
                
                if conv_parts:
                    conversation_context = f"\n\nPREVIOUS CONVERSATION CONTEXT:\n{chr(10).join(conv_parts)}\n\nCURRENT QUESTION (may be a follow-up):\n"
            
            # Prepare prompts
            lang_name = self._get_language_name(language)
            system_prompt = f"""You are a comprehensive information extractor. Answer questions using ONLY the information provided in the context below.

CRITICAL LANGUAGE RULE:
- The question is in {lang_name} language
- You MUST answer in {lang_name} language ONLY
- Do NOT switch to any other language, even if context chunks are in a different language

COMPREHENSIVE EXTRACTION RULES:
1. Use ONLY information from the context - do NOT add any information not explicitly stated
2. Write in natural, flowing prose - do NOT use bullet points, numbered lists (1., 2., 3.), or structured sections
3. Write in continuous sentences, connecting all relevant points naturally

CRITICAL RELEVANCE RULE:
- ONLY include information that DIRECTLY answers the question
- If a chunk in the context talks about a different topic but uses similar words, DO NOT include it
- Filter out any content that doesn't directly relate to the question topic

CRITICAL: Do NOT say "context does not provide" - if information is missing, just omit it."""
            
            user_prompt = f"""Question (in {lang_name}): {question}{conversation_context}

Context from transcripts:
{context}

Provide a clear, comprehensive answer that directly addresses the question. Extract and include ONLY information from the context above that DIRECTLY answers the question. Answer in {lang_name}."""
            
            # Stream response
            stream = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1,
                max_tokens=min(max_length * 3, 1500),
                top_p=0.9,
                stream=True  # Enable streaming
            )
            
            # Yield chunks as they arrive
            full_answer = ""
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_answer += content
                    yield content
            
            # Note: Post-processing (cleaning, validation) would need to be done on full_answer
            # For streaming, we yield raw chunks and do minimal processing
            
        except Exception as e:
            print(f"⚠️  LLM streaming failed: {e}")
            # Fallback: yield simple answer
            answer_parts = []
            for chunk in retrieved_chunks[:3]:
                text = chunk.get('text', '')
                if text:
                    answer_parts.append(text)
            answer = ' '.join(answer_parts)
            for word in answer.split():
                yield word + ' '
            
        except Exception as e:
            print(f"⚠️  LLM refinement failed: {e}")
            return self._refine_simple(question, retrieved_chunks, language)
    
    def _refine_simple(
        self,
        question: str,
        retrieved_chunks: List[Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        """Simple answer refinement (concatenation)"""
        # Combine top chunks
        answer_parts = []
        for chunk in retrieved_chunks[:3]:  # Use top 3
            text = chunk.get('text', '')
            if text:
                answer_parts.append(text)
        
        refined_answer = ' '.join(answer_parts)
        
        # Clean up
        refined_answer = refined_answer.strip()
        if refined_answer and not refined_answer[-1] in '.!?':
            refined_answer += '.'
        
        return {
            'refined_answer': refined_answer,
            'method': 'simple',
            'chunks_used': len(answer_parts),
            'is_from_context': True,
            'context_relevant': True
        }
    
    def answer_general_knowledge(
        self,
        question: str,
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Answer question using general knowledge (when context is not relevant)
        
        Args:
            question: User question
            language: Target language
            
        Returns:
            Dictionary with answer and metadata
        """
        # Handle greetings specially
        question_lower = question.lower().strip()
        greetings_responses = {
            'en': {
                'hi': 'Hello! How can I help you with your transcripts today?',
                'hey': 'Hey! How can I assist you?',
                'hello': 'Hello! What would you like to know about your transcripts?',
                'bye': 'Goodbye! Feel free to come back if you have questions about your transcripts.',
                'thanks': "You're welcome!",
                'thank you': "You're welcome!"
            },
            'hi': {
                'hi': 'नमस्ते! मैं आपकी ट्रांसक्रिप्ट के साथ कैसे मदद कर सकता हूं?',
                'hey': 'नमस्ते! मैं कैसे सहायता कर सकता हूं?',
                'hello': 'नमस्ते! आप अपनी ट्रांसक्रिप्ट के बारे में क्या जानना चाहेंगे?',
                'bye': 'अलविदा! यदि आपके पास अपनी ट्रांसक्रिप्ट के बारे में प्रश्न हैं तो वापस आने के लिए स्वतंत्र महसूस करें।',
                'thanks': 'आपका स्वागत है!',
                'thank you': 'आपका स्वागत है!'
            },
            'te': {
                'hi': 'నమస్కారం! మీ ట్రాన్స్క్రిప్ట్‌ల గురించి నేను ఎలా సహాయం చేయగలను?',
                'hey': 'నమస్కారం! నేను ఎలా సహాయం చేయగలను?',
                'hello': 'నమస్కారం! మీ ట్రాన్స్క్రిప్ట్‌ల గురించి మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారు?',
                'bye': 'వీడ్కోలు! మీ ట్రాన్స్క్రిప్ట్‌ల గురించి ప్రశ్నలు ఉంటే తిరిగి రావడానికి స్వేచ్ఛగా ఉండండి।',
                'thanks': 'స్వాగతం!',
                'thank you': 'స్వాగతం!'
            },
            'ta': {
                'hi': 'வணக்கம்! உங்கள் படிகளுடன் நான் எவ்வாறு உதவ முடியும்?',
                'hey': 'வணக்கம்! நான் எவ்வாறு உதவ முடியும்?',
                'hello': 'வணக்கம்! உங்கள் படிகளைப் பற்றி நீங்கள் என்ன அறிய விரும்புகிறீர்கள்?',
                'bye': 'பிரியாவிடை! உங்கள் படிகளைப் பற்றி கேள்விகள் இருந்தால் திரும்ப வர தயங்க வேண்டாம்।',
                'thanks': 'வரவேற்கிறோம்!',
                'thank you': 'வரவேற்கிறோம்!'
            },
            'kn': {
                'hi': 'ನಮಸ್ಕಾರ! ನಿಮ್ಮ ಪ್ರತಿಲಿಪಿಗಳೊಂದಿಗೆ ನಾನು ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?',
                'hey': 'ನಮಸ್ಕಾರ! ನಾನು ಹೇಗೆ ಸಹಾಯ ಮಾಡಬಹುದು?',
                'hello': 'ನಮಸ್ಕಾರ! ನಿಮ್ಮ ಪ್ರತಿಲಿಪಿಗಳ ಬಗ್ಗೆ ನೀವು ಏನು ತಿಳಿಯಲು ಬಯಸುತ್ತೀರಿ?',
                'bye': 'ವಿದಾಯ! ನಿಮ್ಮ ಪ್ರತಿಲಿಪಿಗಳ ಬಗ್ಗೆ ಪ್ರಶ್ನೆಗಳಿದ್ದರೆ ಮರಳಿ ಬರಲು ಮುಕ್ತವಾಗಿರಿ।',
                'thanks': 'ಸ್ವಾಗತ!',
                'thank you': 'ಸ್ವಾಗತ!'
            },
            'ml': {
                'hi': 'നമസ്കാരം! നിങ്ങളുടെ പ്രതികരണങ്ങളുമായി ഞാൻ എങ്ങനെ സഹായിക്കാം?',
                'hey': 'നമസ്കാരം! ഞാൻ എങ്ങനെ സഹായിക്കാം?',
                'hello': 'നമസ്കാരം! നിങ്ങളുടെ പ്രതികരണങ്ങളെക്കുറിച്ച് നിങ്ങൾ എന്ത് അറിയാൻ ആഗ്രഹിക്കുന്നു?',
                'bye': 'വിട! നിങ്ങളുടെ പ്രതികരണങ്ങളെക്കുറിച്ച് ചോദ്യങ്ങൾ ഉണ്ടെങ്കിൽ തിരികെ വരാൻ മടിക്കരുത്।',
                'thanks': 'സ്വാഗതം!',
                'thank you': 'സ്വാഗതം!'
            },
            'bn': {
                'hi': 'নমস্কার! আমি আপনার ট্রান্সক্রিপ্টগুলির সাথে কীভাবে সাহায্য করতে পারি?',
                'hey': 'নমস্কার! আমি কীভাবে সাহায্য করতে পারি?',
                'hello': 'নমস্কার! আপনি আপনার ট্রান্সক্রিপ্ট সম্পর্কে কী জানতে চান?',
                'bye': 'বিদায়! আপনার ট্রান্সক্রিপ্ট সম্পর্কে প্রশ্ন থাকলে আবার আসতে নির্দ্বিধায়।',
                'thanks': 'স্বাগতম!',
                'thank you': 'স্বাগতম!'
            },
            'mr': {
                'hi': 'नमस्कार! मी तुमच्या ट्रान्सक्रिप्टसह कसे मदत करू शकतो?',
                'hey': 'नमस्कार! मी कसे मदत करू शकतो?',
                'hello': 'नमस्कार! तुम्ही तुमच्या ट्रान्सक्रिप्टबद्दल काय जाणून घ्यायचे आहे?',
                'bye': 'निरोप! तुमच्या ट्रान्सक्रिप्टबद्दल प्रश्न असल्यास परत येण्यास मोकळे वाटा।',
                'thanks': 'स्वागत आहे!',
                'thank you': 'स्वागत आहे!'
            },
            'gu': {
                'hi': 'નમસ્તે! હું તમારી ટ્રાન્સક્રિપ્ટ સાથે કેવી રીતે મદદ કરી શકું?',
                'hey': 'નમસ્તે! હું કેવી રીતે મદદ કરી શકું?',
                'hello': 'નમસ્તે! તમે તમારી ટ્રાન્સક્રિપ્ટ વિશે શું જાણવા માંગો છો?',
                'bye': 'આવજો! તમારી ટ્રાન્સક્રિપ્ટ વિશે પ્રશ્નો હોય તો પાછા આવવા મફત લાગો।',
                'thanks': 'સ્વાગત છે!',
                'thank you': 'સ્વાગત છે!'
            },
            'pa': {
                'hi': 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਤੁਹਾਡੀਆਂ ਟ੍ਰਾਂਸਕ੍ਰਿਪਟਾਂ ਨਾਲ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?',
                'hey': 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਮੈਂ ਕਿਵੇਂ ਮਦਦ ਕਰ ਸਕਦਾ ਹਾਂ?',
                'hello': 'ਸਤ ਸ੍ਰੀ ਅਕਾਲ! ਤੁਸੀਂ ਆਪਣੀਆਂ ਟ੍ਰਾਂਸਕ੍ਰਿਪਟਾਂ ਬਾਰੇ ਕੀ ਜਾਣਨਾ ਚਾਹੁੰਦੇ ਹੋ?',
                'bye': 'ਅਲਵਿਦਾ! ਜੇ ਤੁਹਾਡੀਆਂ ਟ੍ਰਾਂਸਕ੍ਰਿਪਟਾਂ ਬਾਰੇ ਸਵਾਲ ਹਨ ਤਾਂ ਵਾਪਸ ਆਉਣ ਲਈ ਮੁਕਤ ਹੋਵੋ।',
                'thanks': 'ਸਵਾਗਤ ਹੈ!',
                'thank you': 'ਸਵਾਗਤ ਹੈ!'
            },
            'zh': {
                'hi': '你好！我今天如何帮助您处理您的转录？',
                'hey': '你好！我如何帮助您？',
                'hello': '你好！您想了解您的转录的什么？',
                'bye': '再见！如果您对转录有任何问题，请随时回来。',
                'thanks': '不客气！',
                'thank you': '不客气！'
            },
            'ja': {
                'hi': 'こんにちは！今日はあなたの転写についてどのようにお手伝いできますか？',
                'hey': 'こんにちは！どのようにお手伝いできますか？',
                'hello': 'こんにちは！転写について何を知りたいですか？',
                'bye': 'さようなら！転写について質問がある場合は、いつでも戻ってきてください。',
                'thanks': 'どういたしまして！',
                'thank you': 'どういたしまして！'
            },
            'ko': {
                'hi': '안녕하세요! 오늘 전사에 대해 어떻게 도와드릴까요?',
                'hey': '안녕하세요! 어떻게 도와드릴까요?',
                'hello': '안녕하세요! 전사에 대해 무엇을 알고 싶으신가요?',
                'bye': '안녕히 가세요! 전사에 대한 질문이 있으시면 언제든지 돌아오세요।',
                'thanks': '천만에요!',
                'thank you': '천만에요!'
            },
            'ar': {
                'hi': 'مرحبا! كيف يمكنني مساعدتك في نصوصك اليوم؟',
                'hey': 'مرحبا! كيف يمكنني المساعدة؟',
                'hello': 'مرحبا! ماذا تريد أن تعرف عن نصوصك؟',
                'bye': 'وداعا! لا تتردد في العودة إذا كان لديك أسئلة حول نصوصك।',
                'thanks': 'أهلا بك!',
                'thank you': 'أهلا بك!'
            },
            'de': {
                'hi': 'Hallo! Wie kann ich Ihnen heute bei Ihren Transkripten helfen?',
                'hey': 'Hallo! Wie kann ich helfen?',
                'hello': 'Hallo! Was möchten Sie über Ihre Transkripte wissen?',
                'bye': 'Auf Wiedersehen! Kommen Sie gerne zurück, wenn Sie Fragen zu Ihren Transkripten haben।',
                'thanks': 'Bitte sehr!',
                'thank you': 'Bitte sehr!'
            },
            'fr': {
                'hi': 'Bonjour! Comment puis-je vous aider avec vos transcriptions aujourd\'hui?',
                'hey': 'Bonjour! Comment puis-je vous aider?',
                'hello': 'Bonjour! Que souhaitez-vous savoir sur vos transcriptions?',
                'bye': 'Au revoir! N\'hésitez pas à revenir si vous avez des questions sur vos transcriptions।',
                'thanks': 'De rien!',
                'thank you': 'De rien!'
            },
            'es': {
                'hi': '¡Hola! ¿Cómo puedo ayudarte con tus transcripciones hoy?',
                'hey': '¡Hola! ¿Cómo puedo ayudarte?',
                'hello': '¡Hola! ¿Qué te gustaría saber sobre tus transcripciones?',
                'bye': '¡Adiós! Siéntete libre de volver si tienes preguntas sobre tus transcripciones।',
                'thanks': '¡De nada!',
                'thank you': '¡De nada!'
            },
            'it': {
                'hi': 'Ciao! Come posso aiutarti con le tue trascrizioni oggi?',
                'hey': 'Ciao! Come posso aiutarti?',
                'hello': 'Ciao! Cosa vorresti sapere sulle tue trascrizioni?',
                'bye': 'Arrivederci! Sentiti libero di tornare se hai domande sulle tue trascrizioni।',
                'thanks': 'Prego!',
                'thank you': 'Prego!'
            },
            'pt': {
                'hi': 'Olá! Como posso ajudá-lo com suas transcrições hoje?',
                'hey': 'Olá! Como posso ajudar?',
                'hello': 'Olá! O que você gostaria de saber sobre suas transcrições?',
                'bye': 'Tchau! Sinta-se à vontade para voltar se tiver perguntas sobre suas transcrições।',
                'thanks': 'De nada!',
                'thank you': 'De nada!'
            },
            'ru': {
                'hi': 'Привет! Как я могу помочь вам с вашими транскриптами сегодня?',
                'hey': 'Привет! Как я могу помочь?',
                'hello': 'Привет! Что вы хотели бы узнать о ваших транскриптах?',
                'bye': 'До свидания! Не стесняйтесь вернуться, если у вас есть вопросы о ваших транскриптах।',
                'thanks': 'Пожалуйста!',
                'thank you': 'Пожалуйста!'
            },
            'th': {
                'hi': 'สวัสดี! ฉันจะช่วยคุณเกี่ยวกับการถอดความของคุณได้อย่างไรวันนี้?',
                'hey': 'สวัสดี! ฉันจะช่วยได้อย่างไร?',
                'hello': 'สวัสดี! คุณต้องการทราบอะไรเกี่ยวกับการถอดความของคุณ?',
                'bye': 'ลาก่อน! อย่าลังเลที่จะกลับมาถ้าคุณมีคำถามเกี่ยวกับการถอดความของคุณ।',
                'thanks': 'ยินดี!',
                'thank you': 'ยินดี!'
            },
            'vi': {
                'hi': 'Xin chào! Tôi có thể giúp gì cho bạn với bản ghi của bạn hôm nay?',
                'hey': 'Xin chào! Tôi có thể giúp gì?',
                'hello': 'Xin chào! Bạn muốn biết gì về bản ghi của bạn?',
                'bye': 'Tạm biệt! Hãy quay lại nếu bạn có câu hỏi về bản ghi của bạn।',
                'thanks': 'Không có gì!',
                'thank you': 'Không có gì!'
            },
            'tr': {
                'hi': 'Merhaba! Bugün transkriptlerinizle nasıl yardımcı olabilirim?',
                'hey': 'Merhaba! Nasıl yardımcı olabilirim?',
                'hello': 'Merhaba! Transkriptleriniz hakkında ne bilmek istersiniz?',
                'bye': 'Güle güle! Transkriptleriniz hakkında sorularınız varsa geri dönmekten çekinmeyin।',
                'thanks': 'Rica ederim!',
                'thank you': 'Rica ederim!'
            }
        }
        
        # Check if it's a greeting
        lang_responses = greetings_responses.get(language, greetings_responses['en'])
        if question_lower in lang_responses:
            response = lang_responses.get(question_lower)
            if response:
                return {
                    'answer': response,
                    'method': 'greeting',
                    'is_from_context': False
                }
        
        if self.use_llm and self.groq_client:
            return self._answer_general_with_llm(question, language)
        else:
            return {
                'answer': self._get_fallback_message(language),
                'method': 'fallback',
                'is_from_context': False
            }
    
    def _answer_general_with_llm(self, question: str, language: str) -> Dict[str, Any]:
        """Answer using general knowledge with LLM"""
        try:
            language_instruction = f"Answer in {language} language." if language != 'en' else ""
            
            prompt = f"""The user asked a question that is not related to their stored transcripts.
Answer the question using your general knowledge. Be helpful and friendly.
{language_instruction}

Question: {question}

Provide a clear, concise answer:"""

            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Answer questions clearly and concisely."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            answer = response.choices[0].message.content.strip()
            
            return {
                'answer': answer,
                'method': 'general_knowledge',
                'is_from_context': False
            }
            
        except Exception as e:
            print(f"⚠️  General knowledge answer failed: {e}")
            return {
                'answer': self._get_fallback_message(language),
                'method': 'fallback',
                'is_from_context': False
            }

    def _get_language_name(self, language_code: str) -> str:
        """Get language name from code"""
        return self.LANGUAGE_NAMES.get(language_code, language_code.upper())
    
    def _get_fallback_message(self, language: str) -> str:
        """Get fallback message in the specified language"""
        fallback_messages = {
            'en': 'I cannot answer this question as it is not related to your stored transcripts. Please ask questions about your uploaded content.',
            'hi': 'मैं इस प्रश्न का उत्तर नहीं दे सकता क्योंकि यह आपके संग्रहीत ट्रांसक्रिप्ट से संबंधित नहीं है। कृपया अपनी अपलोड की गई सामग्री के बारे में प्रश्न पूछें।',
            'te': 'నేను ఈ ప్రశ్నకు సమాధానం ఇవ్వలేను ఎందుకంటే ఇది మీ నిల్వ ఉన్న ట్రాన్స్క్రిప్ట్‌లకు సంబంధించినది కాదు। దయచేసి మీ అప్‌లోడ్ చేసిన కంటెంట్ గురించి ప్రశ్నలు అడగండి।',
            'ta': 'இந்த கேள்விக்கு நான் பதிலளிக்க முடியாது, ஏனெனில் இது உங்கள் சேமிக்கப்பட்ட படிகளுடன் தொடர்புடையது அல்ல। தயவுசெய்து உங்கள் பதிவேற்றிய உள்ளடக்கத்தைப் பற்றி கேள்விகள் கேளுங்கள்।',
            'kn': 'ಈ ಪ್ರಶ್ನೆಗೆ ನಾನು ಉತ್ತರಿಸಲು ಸಾಧ್ಯವಿಲ್ಲ ಏಕೆಂದರೆ ಇದು ನಿಮ್ಮ ಸಂಗ್ರಹಿಸಿದ ಪ್ರತಿಲಿಪಿಗಳಿಗೆ ಸಂಬಂಧಿಸಿದ್ದಲ್ಲ। ದಯವಿಟ್ಟು ನಿಮ್ಮ ಅಪ್‌ಲೋಡ್ ಮಾಡಿದ ವಿಷಯದ ಬಗ್ಗೆ ಪ್ರಶ್ನೆಗಳನ್ನು ಕೇಳಿ।',
            'ml': 'ഈ ചോദ്യത്തിന് എനിക്ക് ഉത്തരം നൽകാൻ കഴിയില്ല കാരണം ഇത് നിങ്ങളുടെ സംഭരിച്ച പ്രതികരണങ്ങളുമായി ബന്ധപ്പെട്ടതല്ല। ദയവായി നിങ്ങളുടെ അപ്‌ലോഡ് ചെയ്ത ഉള്ളടക്കത്തെക്കുറിച്ച് ചോദ്യങ്ങൾ ചോദിക്കുക।',
            'bn': 'আমি এই প্রশ্নের উত্তর দিতে পারি না কারণ এটি আপনার সংরক্ষিত ট্রান্সক্রিপ্টের সাথে সম্পর্কিত নয়। অনুগ্রহ করে আপনার আপলোড করা বিষয়বস্তু সম্পর্কে প্রশ্ন করুন।',
            'mr': 'मी या प्रश्नाचे उत्तर देऊ शकत नाही कारण ते तुमच्या संग्रहित ट्रान्सक्रिप्टशी संबंधित नाही। कृपया तुमच्या अपलोड केलेल्या सामग्रीबद्दल प्रश्न विचारा।',
            'gu': 'હું આ પ્રશ્નનો જવાબ આપી શકતો નથી કારણ કે તે તમારા સંગ્રહિત ટ્રાન્સક્રિપ્ટ સાથે સંબંધિત નથી। કૃપા કરીને તમારી અપલોડ કરેલી સામગ્રી વિશે પ્રશ્નો પૂછો।',
            'pa': 'ਮੈਂ ਇਸ ਸਵਾਲ ਦਾ ਜਵਾਬ ਨਹੀਂ ਦੇ ਸਕਦਾ ਕਿਉਂਕਿ ਇਹ ਤੁਹਾਡੀਆਂ ਸੰਗ੍ਰਹਿਤ ਟ੍ਰਾਂਸਕ੍ਰਿਪਟਾਂ ਨਾਲ ਸੰਬੰਧਿਤ ਨਹੀਂ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣੀ ਅਪਲੋਡ ਕੀਤੀ ਸਮਗਰੀ ਬਾਰੇ ਪ੍ਰਸ਼ਨ ਪੁੱਛੋ।',
            'zh': '我无法回答这个问题，因为它与您存储的转录无关。请询问您上传的内容。',
            'ja': 'この質問にはお答えできません。保存された転写に関連していないためです。アップロードしたコンテンツについて質問してください。',
            'ko': '이 질문에 답할 수 없습니다. 저장된 전사와 관련이 없기 때문입니다. 업로드한 콘텐츠에 대해 질문해 주세요。',
            'ar': 'لا أستطيع الإجابة على هذا السؤال لأنه لا يتعلق بنصوصك المخزنة. يرجى طرح أسئلة حول المحتوى الذي قمت بتحميله।',
            'de': 'Ich kann diese Frage nicht beantworten, da sie nicht mit Ihren gespeicherten Transkripten zusammenhängt. Bitte stellen Sie Fragen zu Ihrem hochgeladenen Inhalt।',
            'fr': 'Je ne peux pas répondre à cette question car elle n\'est pas liée à vos transcriptions stockées. Veuillez poser des questions sur votre contenu téléchargé।',
            'es': 'No puedo responder esta pregunta porque no está relacionada con sus transcripciones almacenadas. Por favor, haga preguntas sobre su contenido cargado।',
            'it': 'Non posso rispondere a questa domanda perché non è correlata alle tue trascrizioni memorizzate. Per favore, fai domande sul tuo contenuto caricato।',
            'pt': 'Não posso responder a esta pergunta porque não está relacionada às suas transcrições armazenadas. Por favor, faça perguntas sobre seu conteúdo carregado।',
            'ru': 'Я не могу ответить на этот вопрос, так как он не связан с вашими сохраненными транскриптами. Пожалуйста, задавайте вопросы о вашем загруженном контенте।',
            'th': 'ฉันไม่สามารถตอบคำถามนี้ได้เพราะไม่เกี่ยวข้องกับสำเนาที่เก็บไว้ของคุณ กรุณาถามคำถามเกี่ยวกับเนื้อหาที่คุณอัปโหลด।',
            'vi': 'Tôi không thể trả lời câu hỏi này vì nó không liên quan đến bản ghi đã lưu của bạn. Vui lòng đặt câu hỏi về nội dung bạn đã tải lên।',
            'tr': 'Bu soruyu yanıtlayamam çünkü saklanan transkriptlerinizle ilgili değil. Lütfen yüklediğiniz içerik hakkında sorular sorun।'
        }
        return fallback_messages.get(language, fallback_messages['en'])
    
    def _filter_irrelevant_chunks(self, chunks: List[Dict[str, Any]], question: Optional[str] = None) -> List[Dict[str, Any]]:
        """Filter out irrelevant/noise chunks and chunks not related to the question"""
        import re
        
        # Patterns that indicate irrelevant/test content
        noise_patterns = [
            r'You are listening to a sample MP3 audio file',
            r'samplefiles\.com',
            r'sample.*audio.*file',
            r'test.*content',
            r'placeholder.*text',
            r'lorem ipsum',
        ]
        
        filtered_chunks = []
        for chunk in chunks:
            text = chunk.get('text', '') or chunk.get('content', '') or chunk.get('chunk_text', '')
            if not text:
                continue
            
            # Check if chunk contains noise patterns
            is_noise = False
            text_lower = text.lower()
            for pattern in noise_patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    is_noise = True
                    break
            
            if is_noise:
                continue
            
            # NEW: Check if chunk is relevant to the question topic
            if question:
                if not self._is_chunk_relevant_to_question(chunk, question):
                    continue  # Skip chunks that don't relate to the question
            
            filtered_chunks.append(chunk)
        
        return filtered_chunks if filtered_chunks else chunks  # Return original if all filtered out
    
    def _is_chunk_relevant_to_question(self, chunk: Dict[str, Any], question: str) -> bool:
        """Check if a chunk is actually relevant to the question using semantic similarity"""
        import numpy as np
        
        text = chunk.get('text', '') or chunk.get('content', '') or chunk.get('chunk_text', '')
        if not text or not text.strip():
            return False
        
        # If no embedder available, fall back to keyword matching
        if not self.embedder:
            return self._is_chunk_relevant_keyword_fallback(chunk, question)
        
        try:
            # Compute embeddings for question and chunk
            question_embedding = self.embedder.embed_text(question)
            chunk_embedding = self.embedder.embed_text(text)
            
            # Calculate cosine similarity
            question_norm = question_embedding / (np.linalg.norm(question_embedding) or 1.0)
            chunk_norm = chunk_embedding / (np.linalg.norm(chunk_embedding) or 1.0)
            similarity = float(np.dot(question_norm, chunk_norm))
            
            # STRICTER threshold: chunks with similarity >= 0.62 are considered relevant
            # BGE-m3 provides better embeddings, so we can use stricter thresholds
            # This is stricter than initial retrieval (which uses 0.2-0.3) to filter false positives
            # For multilingual content with BGE-m3, we can be stricter while maintaining quality
            relevance_threshold = 0.62  # Increased from 0.58 to 0.62 - BGE-m3 allows stricter filtering
            
            is_relevant = similarity >= relevance_threshold
            
            if not is_relevant:
                print(f"🔍 Filtered chunk (similarity: {similarity:.3f} < {relevance_threshold}): {text[:100]}...")
            
            return is_relevant
            
        except Exception as e:
            print(f"⚠️  Semantic relevance check failed: {e}, using fallback")
            return self._is_chunk_relevant_keyword_fallback(chunk, question)
    
    def _is_chunk_relevant_keyword_fallback(self, chunk: Dict[str, Any], question: str) -> bool:
        """Fallback keyword-based check if semantic similarity fails"""
        import re
        
        text = chunk.get('text', '') or chunk.get('content', '') or chunk.get('chunk_text', '')
        if not text:
            return False
        
        question_lower = question.lower().strip()
        text_lower = text.lower()
        
        # Extract meaningful words (4+ chars)
        question_words = set(re.findall(r'\b\w{4,}\b', question_lower))
        text_words = set(re.findall(r'\b\w{4,}\b', text_lower))
        
        # Remove common stop words
        stop_words = {'what', 'how', 'why', 'when', 'where', 'who', 'which', 'that', 'this', 
                      'with', 'from', 'have', 'been', 'were', 'will', 'would', 'could', 'should', 
                      'about', 'their', 'there', 'these', 'those', 'them', 'they', 'then', 'than'}
        
        question_topics = question_words - stop_words
        text_topics = text_words - stop_words
        
        if not question_topics:
            return True  # If no topics extracted, assume relevant
        
        # Check topic overlap
        overlap = len(question_topics & text_topics)
        overlap_ratio = overlap / len(question_topics) if question_topics else 0
        
        # Need at least 30% topic overlap
        return overlap_ratio >= 0.3
    
    def _clean_answer_format(self, answer: str) -> str:
        """Remove verbose sections and make answer natural"""
        import re
        
        # Remove common verbose section headers
        patterns_to_remove = [
            r'\*\*Direct Answer to the Question:\*\*',
            r'\*\*Specific Facts with Numbers/Dates:\*\*',
            r'\*\*Relevant Points and Impacts:\*\*',
            r'\*\*Relevant Details from Context:\*\*',
            r'\*\*Summary:\*\*',
            r'^Direct Answer to the Question:',
            r'^Specific Facts with Numbers/Dates:',
            r'^Relevant Points and Impacts:',
            r'^Relevant Details from Context:',
            r'^Summary:',
            r'^\*\*Direct Answer:\*\*',
            r'^\*\*Specific Facts:\*\*',
            r'^\*\*Relevant Points:\*\*',
        ]
        
        for pattern in patterns_to_remove:
            answer = re.sub(pattern, '', answer, flags=re.IGNORECASE | re.MULTILINE)
        
        # Remove numbered lists formatting - more aggressive
        # Pattern: "1. " or "1) " at start of line
        answer = re.sub(r'^\d+[\.\)]\s+', '', answer, flags=re.MULTILINE)
        # Pattern: "1. " or "1) " anywhere (for inline lists)
        answer = re.sub(r'\n\d+[\.\)]\s+', ' ', answer)
        answer = re.sub(r'\s+\d+[\.\)]\s+', ' ', answer)
        
        # Remove bullet points
        answer = re.sub(r'^[-•*]\s+', '', answer, flags=re.MULTILINE)
        answer = re.sub(r'\n[-•*]\s+', ' ', answer)
        
        # Split into lines and process
        lines = answer.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Remove any remaining numbered list markers
            line = re.sub(r'^\d+[\.\)]\s*', '', line)
            # Remove bullet points
            line = re.sub(r'^[-•*]\s*', '', line)
            if line:
                cleaned_lines.append(line)
        
        # Join into natural prose with proper sentence structure
        cleaned_answer = ' '.join(cleaned_lines)
        
        # Clean up extra whitespace but preserve sentence breaks
        cleaned_answer = re.sub(r'\s+', ' ', cleaned_answer)
        cleaned_answer = re.sub(r'\s+([.!?])\s+', r'\1 ', cleaned_answer)  # Fix spacing around punctuation
        cleaned_answer = re.sub(r'\n{3,}', '\n\n', cleaned_answer)
        
        return cleaned_answer.strip()
    
    def _validate_no_hallucination(self, answer: str, context: str) -> str:
        """Remove any facts from answer that are not in context"""
        import re
        
        # Filter out sample/test content from context
        context = re.sub(r'You are listening to a sample MP3 audio file[^.]*\.', '', context, flags=re.IGNORECASE)
        context = re.sub(r'samplefiles\.com[^.]*\.', '', context, flags=re.IGNORECASE)
        context = re.sub(r'sample.*audio.*file[^.]*\.', '', context, flags=re.IGNORECASE)
        
        # Key phrases that indicate hallucination (including variations)
        hallucination_phrases = [
            'previous prime minister',
            'former prime minister',
            'always stable',
            'consistently been a stable',
            'consistently stable',
            'stable figure',
            'always present',
            'always guiding',
            'consistently present',
            'observed by everyone',
            'as we have all observed',
            'as observed by everyone',
            'we have all observed',
            'everyone has observed',
            'common sense',
            'generally known',
            'sample MP3',
            'samplefiles',
            'You are listening',
        ]
        
        # Phrases that indicate disclaimers (should be removed)
        disclaimer_phrases = [
            'context does not provide',
            'the context does not',
            'context doesn\'t provide',
            'the context doesn\'t',
            'I cannot find',
            'I don\'t have',
            'not available in the context',
            'not mentioned in the context',
        ]
        
        # Check if answer contains hallucination phrases not in context
        answer_lower = answer.lower()
        context_lower = context.lower()
        
        # Remove sentences containing disclaimer phrases
        sentences = re.split(r'[.!?]\s+', answer)
        filtered_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check for disclaimer phrases - remove entire sentence
            has_disclaimer = False
            for phrase in disclaimer_phrases:
                if phrase in sentence.lower():
                    has_disclaimer = True
                    break
            
            if has_disclaimer:
                continue  # Skip sentences with disclaimers
            
            # Check for hallucination phrases (including partial matches)
            has_hallucination = False
            sentence_lower = sentence.lower()
            for phrase in hallucination_phrases:
                if phrase in sentence_lower:
                    # Check if phrase appears in context
                    if phrase not in context_lower:
                        # Also check for variations (e.g., "stable" alone might be OK, but "always stable" is not)
                        # If the sentence contains multiple hallucination indicators, it's likely hallucination
                        if phrase in ['stable figure', 'always present', 'always guiding', 'consistently been']:
                            # These are strong indicators - check if context has similar but different phrasing
                            # If context doesn't have these exact phrases, it's likely hallucination
                            has_hallucination = True
                            break
                        elif phrase in ['always stable', 'consistently stable']:
                            # Direct hallucination phrase
                            has_hallucination = True
                            break
                        # For other phrases, check if they appear in context
                        elif phrase not in context_lower:
                            has_hallucination = True
                            break
            
            # Additional check: If sentence contains "stable" or "consistently" but context doesn't mention these
            if not has_hallucination:
                if ('stable' in sentence_lower or 'consistently' in sentence_lower) and 'stable' not in context_lower and 'consistently' not in context_lower:
                    # Check if it's about prime minister being stable - this is likely hallucination
                    if 'prime minister' in sentence_lower:
                        has_hallucination = True
            
            if not has_hallucination:
                filtered_sentences.append(sentence)
        
        answer = '. '.join(filtered_sentences)
        if answer and not answer.endswith(('.', '!', '?')):
            answer += '.'
        
        # Check for contradictions - "limited to paper" AND "impact" is contradictory
        answer_lower = answer.lower()
        if 'limited to paper' in answer_lower or 'limited to papers' in answer_lower:
            if 'impact' in answer_lower or 'ground level' in answer_lower or 'grassroots' in answer_lower:
                # Check context to see which one is actually stated
                if 'limited to paper' not in context_lower and 'limited to papers' not in context_lower:
                    # Remove "limited to paper" if not in context
                    answer = re.sub(r'[^.]*limited to paper[^.]*\.', '', answer, flags=re.IGNORECASE)
                elif 'impact' not in context_lower and 'ground level' not in context_lower and 'grassroots' not in context_lower:
                    # Remove "impact" if not in context
                    answer = re.sub(r'[^.]*impact[^.]*\.', '', answer, flags=re.IGNORECASE)
                else:
                    # Both might be in context but contradictory - check if they're in same sentence
                    # If they're in the same sentence, it's likely a contradiction - remove the sentence
                    sentences = re.split(r'[.!?]\s+', answer)
                    filtered = []
                    for sent in sentences:
                        sent_lower = sent.lower()
                        if ('limited to paper' in sent_lower or 'limited to papers' in sent_lower) and ('impact' in sent_lower or 'ground level' in sent_lower):
                            # Contradictory sentence - check context
                            if 'not only' in sent_lower or 'but also' in sent_lower:
                                # This is a contradiction pattern - remove it
                                continue
                        filtered.append(sent)
                    answer = '. '.join(filtered)
        
        # Remove repetition - if same phrase appears twice, keep only one
        sentences = answer.split('. ')
        seen_phrases = set()
        unique_sentences = []
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            sent_key = sent.lower().strip()[:50]  # Use first 50 chars as key
            if sent_key not in seen_phrases:
                seen_phrases.add(sent_key)
                unique_sentences.append(sent)
            # Also check for very similar sentences
            elif sent.strip() not in [s.strip() for s in unique_sentences]:
                unique_sentences.append(sent)
        
        answer = '. '.join(unique_sentences)
        
        return answer.strip()
    
    def _verify_grounding(self, answer: str, context: str) -> str:
        """Verify each sentence is grounded in context"""
        import re
        
        # Split answer into sentences
        sentences = re.split(r'[.!?]\s+', answer)
        grounded_sentences = []
        context_lower = context.lower()
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check if sentence has substantial overlap with context
            # Extract key words from sentence (excluding common words)
            sentence_lower = sentence.lower()
            sentence_words = set(re.findall(r'\b\w{4,}\b', sentence_lower))  # Words with 4+ chars
            context_words = set(re.findall(r'\b\w{4,}\b', context_lower))
            
            # Remove common stop words
            stop_words = {'that', 'this', 'with', 'from', 'have', 'been', 'were', 'will', 'would', 'could', 'should', 'about', 'their', 'there', 'these', 'those', 'which', 'where', 'when', 'what', 'them', 'they', 'then', 'than'}
            sentence_words = sentence_words - stop_words
            context_words = context_words - stop_words
            
            # Check overlap
            if len(sentence_words) == 0:
                # Sentence has no meaningful words, skip
                continue
            
            overlap_ratio = len(sentence_words & context_words) / len(sentence_words) if sentence_words else 0
            
            # If less than 30% of key words overlap with context, it might be hallucination
            # But also check if it contains known hallucination phrases
            has_known_hallucination = any(phrase in sentence_lower for phrase in [
                'always stable', 'consistently stable', 'stable figure', 'always present', 
                'always guiding', 'consistently been', 'observed by everyone'
            ])
            
            if has_known_hallucination:
                # Check if these phrases appear in context
                if not any(phrase in context_lower for phrase in [
                    'always stable', 'consistently stable', 'stable figure', 'always present',
                    'always guiding', 'consistently been', 'observed by everyone'
                ]):
                    # Known hallucination phrase not in context - skip
                    continue
            
            # If overlap is too low and sentence is long, might be hallucination
            if overlap_ratio < 0.3 and len(sentence_words) > 5:
                # Low overlap with context - might be hallucination
                # But keep it if it's a short factual statement
                if len(sentence_words) > 8:  # Long sentence with low overlap - likely hallucination
                    continue
            
            grounded_sentences.append(sentence)
        
        answer = '. '.join(grounded_sentences)
        if answer and not answer.endswith(('.', '!', '?')):
            answer += '.'
        
        return answer.strip()
    
    def _filter_irrelevant_sentences(self, answer: str, question: str, context: str) -> str:
        """Remove sentences from answer that don't actually answer the question using semantic similarity"""
        import re
        import numpy as np
        
        if not self.embedder:
            # Fallback to keyword-based if no embedder
            return self._filter_irrelevant_sentences_keyword(answer, question, context)
        
        # Split answer into sentences
        sentences = re.split(r'[.!?]\s+', answer)
        relevant_sentences = []
        
        try:
            question_embedding = self.embedder.embed_text(question)
            question_norm = question_embedding / (np.linalg.norm(question_embedding) or 1.0)
            
            # Limit context size for embedding (to avoid token limits)
            context_for_embedding = context[:2000] if len(context) > 2000 else context
            context_embedding = self.embedder.embed_text(context_for_embedding)
            context_norm = context_embedding / (np.linalg.norm(context_embedding) or 1.0)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence or len(sentence) < 10:
                    continue
                
                # Compute semantic similarity between question and sentence
                sentence_embedding = self.embedder.embed_text(sentence)
                sentence_norm = sentence_embedding / (np.linalg.norm(sentence_embedding) or 1.0)
                q_similarity = float(np.dot(question_norm, sentence_norm))
                
                # Also check if sentence is grounded in context
                ctx_similarity = float(np.dot(sentence_norm, context_norm))
                
                # STRICTER thresholds for multilingual content:
                # 1. Relevant to question (similarity >= 0.55, increased from 0.5)
                # 2. Grounded in context (similarity >= 0.45, increased from 0.4)
                # This helps filter out sentences that use similar words but are about different topics
                if q_similarity >= 0.55 and ctx_similarity >= 0.45:
                    relevant_sentences.append(sentence)
                else:
                    print(f"🔍 Filtered sentence (q_sim: {q_similarity:.3f}, ctx_sim: {ctx_similarity:.3f}): {sentence[:80]}...")
            
        except Exception as e:
            print(f"⚠️  Semantic sentence filtering failed: {e}, using keyword fallback")
            return self._filter_irrelevant_sentences_keyword(answer, question, context)
        
        # Join relevant sentences
        filtered_answer = '. '.join(relevant_sentences)
        if filtered_answer and not filtered_answer.endswith(('.', '!', '?')):
            filtered_answer += '.'
        
        return filtered_answer.strip()
    
    def _remove_irrelevant_phrases(self, answer: str, question: str, language: str) -> str:
        """Remove sentences that are semantically irrelevant to the question (language-agnostic)"""
        import re
        import numpy as np
        
        # Split answer into sentences
        sentences = re.split(r'[.!?]\s+', answer)
        filtered_sentences = []
        
        if not self.embedder:
            # No embedder - skip this check, return original answer
            return answer
        
        try:
            # Compute question embedding once
            question_embedding = self.embedder.embed_text(question)
            question_norm = question_embedding / (np.linalg.norm(question_embedding) or 1.0)
            
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence or len(sentence) < 10:
                    # Keep very short sentences (they might be fragments)
                    if sentence:
                        filtered_sentences.append(sentence)
                    continue
                
                # Compute semantic similarity between question and sentence
                sentence_embedding = self.embedder.embed_text(sentence)
                sentence_norm = sentence_embedding / (np.linalg.norm(sentence_embedding) or 1.0)
                similarity = float(np.dot(question_norm, sentence_norm))
                
                # Use strict threshold (0.5) - if sentence is not relevant to question, remove it
                # This catches cases where semantic filtering at chunk level missed something
                # Works for ANY language and ANY question topic
                if similarity >= 0.5:
                    filtered_sentences.append(sentence)
                else:
                    print(f"🔍 Removed irrelevant sentence (sim: {similarity:.3f}): {sentence[:80]}...")
            
        except Exception as e:
            print(f"⚠️  Irrelevant phrase removal failed: {e}, keeping original answer")
            return answer
        
        # Join filtered sentences
        filtered_answer = '. '.join(filtered_sentences)
        if filtered_answer and not filtered_answer.endswith(('.', '!', '?')):
            filtered_answer += '.'
        
        return filtered_answer.strip()
    
    def _filter_irrelevant_sentences_keyword(self, answer: str, question: str, context: str) -> str:
        """Fallback keyword-based sentence filtering"""
        import re
        
        # Split answer into sentences
        sentences = re.split(r'[.!?]\s+', answer)
        relevant_sentences = []
        
        question_lower = question.lower().strip()
        context_lower = context.lower()
        
        # Extract question topic
        question_words = set(re.findall(r'\b\w{4,}\b', question_lower))
        stop_words = {'what', 'how', 'why', 'when', 'where', 'who', 'which', 'that', 'this', 'with', 'from', 'have', 'been', 'were', 'will', 'would', 'could', 'should', 'about', 'their', 'there', 'these', 'those', 'them', 'they', 'then', 'than', 'does', 'doesnt', 'dont', 'doesn'}
        question_topics = question_words - stop_words
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            sentence_lower = sentence.lower()
            
            # Extract key words from sentence
            sentence_words = set(re.findall(r'\b\w{4,}\b', sentence_lower))
            sentence_topics = sentence_words - stop_words
            
            # Check topic overlap
            is_relevant = False
            if question_topics:
                topic_overlap = len(question_topics & sentence_topics)
                if topic_overlap / len(question_topics) >= 0.2:  # At least 20% topic overlap
                    is_relevant = True
            
            # Check if sentence appears in context (grounding check)
            if is_relevant:
                sentence_keywords = {w for w in sentence_topics if len(w) > 3}
                context_keywords = set(re.findall(r'\b\w{4,}\b', context_lower))
                overlap = len(sentence_keywords & context_keywords)
                if sentence_keywords and overlap / len(sentence_keywords) < 0.2:
                    # Low overlap with context - might be hallucination
                    is_relevant = False
            
            if is_relevant:
                relevant_sentences.append(sentence)
        
        # Join relevant sentences
        filtered_answer = '. '.join(relevant_sentences)
        if filtered_answer and not filtered_answer.endswith(('.', '!', '?')):
            filtered_answer += '.'
        
        return filtered_answer.strip()