"""
LangChain-based RAG QA System
Improved answer generation using LangChain chains and prompts
Universal language support for all languages
"""
from typing import List, Dict, Any, Optional
import os

try:
    from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
    from langchain_core.language_models.llms import LLM
    from langchain_core.callbacks.manager import CallbackManagerForLLMRun
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Try older version imports
    try:
        from langchain.prompts import ChatPromptTemplate, PromptTemplate
        from langchain.llms.base import LLM
        from langchain.callbacks.manager import CallbackManagerForLLMRun
        from langchain.schema.runnable import RunnablePassthrough
        from langchain.schema.output_parser import StrOutputParser
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        ChatPromptTemplate = None
        PromptTemplate = None

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None


class GroqLLM(LLM):
    """LangChain wrapper for Groq LLM"""
    
    # Use model_name instead of model to avoid Pydantic validation issues with LLM base class
    model_name: str = "llama-3.1-8b-instant"
    temperature: float = 0.3
    client: Any = None
    
    def __init__(self, model: str = "llama-3.1-8b-instant", temperature: float = 0.3, **kwargs):
        # Initialize base class first (don't pass model/temperature to avoid Pydantic validation)
        super().__init__(**kwargs)
        
        # Set attributes after initialization to avoid Pydantic validation errors
        object.__setattr__(self, 'model_name', model)
        object.__setattr__(self, 'temperature', temperature)
        
        # Then set up Groq client
        api_key = os.getenv("GROQ_API_KEY")
        if api_key and GROQ_AVAILABLE:
            object.__setattr__(self, 'client', Groq(api_key=api_key))
        else:
            object.__setattr__(self, 'client', None)
    
    @property
    def _llm_type(self) -> str:
        return "groq"
    
    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        if not self.client:
            raise ValueError("Groq client not initialized. Set GROQ_API_KEY.")
        
        response = self.client.chat.completions.create(
            model=self.model_name,  # Use model_name instead of model
            messages=[{"role": "user", "content": prompt}],
            temperature=self.temperature,
            **kwargs
        )
        
        return response.choices[0].message.content.strip()


class LangChainRAGQA:
    """
    LangChain-based RAG QA System
    Uses LangChain for better prompt management and answer generation
    Universal language support - works for ALL languages
    """
    
    # Language names mapping for better prompts
    LANGUAGE_NAMES = {
        'en': 'English',
        'hi': 'Hindi',
        'te': 'Telugu',
        'ta': 'Tamil',
        'kn': 'Kannada',
        'ml': 'Malayalam',
        'gu': 'Gujarati',
        'pa': 'Punjabi',
        'bn': 'Bengali',
        'mr': 'Marathi',
        'or': 'Odia',
        'as': 'Assamese',
        'de': 'German',
        'fr': 'French',
        'es': 'Spanish',
        'it': 'Italian',
        'pt': 'Portuguese',
        'nl': 'Dutch',
        'ru': 'Russian',
        'pl': 'Polish',
        'uk': 'Ukrainian',
        'zh': 'Chinese',
        'ja': 'Japanese',
        'ko': 'Korean',
        'ar': 'Arabic',
        'th': 'Thai',
        'vi': 'Vietnamese',
        'tr': 'Turkish',
        'he': 'Hebrew',
        'cs': 'Czech',
        'sv': 'Swedish',
        'no': 'Norwegian',
        'fi': 'Finnish',
        'da': 'Danish',
        'el': 'Greek',
        'hu': 'Hungarian',
        'ro': 'Romanian',
        'bg': 'Bulgarian',
        'hr': 'Croatian',
        'sk': 'Slovak',
        'sl': 'Slovenian',
        'sr': 'Serbian',
    }
    
    def __init__(self, use_langchain: bool = True):
        """
        Initialize LangChain RAG QA
        
        Args:
            use_langchain: Use LangChain (default: True)
        """
        self.use_langchain = use_langchain and LANGCHAIN_AVAILABLE and GROQ_AVAILABLE
        
        if self.use_langchain:
            try:
                self.llm = GroqLLM(model="llama-3.1-8b-instant", temperature=0.1)  # Low temperature for factuality, allow comprehensive extraction
                print("✅ LangChain RAG QA initialized")
            except Exception as e:
                print(f"⚠️  Failed to initialize LangChain: {e}")
                self.use_langchain = False
        else:
            self.llm = None
    
    def _get_language_name(self, language_code: str) -> str:
        """Get language name from code"""
        return self.LANGUAGE_NAMES.get(language_code, language_code.upper())
    
    def _create_multilingual_prompt(self, language: str) -> tuple:
        """
        Create system and user prompts for any language
        Uses universal template that works for all languages
        """
        lang_name = self._get_language_name(language)
        
        # Universal system prompt template (works for all languages)
        # The LLM will understand and respond in the target language
        system_prompt = f"""You are a comprehensive information extractor. Answer questions using ONLY the information provided in the context.

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

ANTI-HALLUCINATION (STRICT):
- Verify every fact exists EXACTLY in context before mentioning it
- Do NOT infer, assume, or add general knowledge
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

CRITICAL: Do NOT say "context does not provide" or "the context doesn't mention" - if information is missing, just omit it. Never use disclaimers.

Write a clear, comprehensive, natural answer in {lang_name}. Include ALL relevant changes, facts, or details mentioned in the context, including specific numbers and dates. Write in flowing prose as continuous sentences. Do NOT use numbered lists (1., 2., 3.) or bullet points."""
        
        # Universal user template (works for all languages)
        user_template = """Question (in {language}): {{question}}

Context (MULTIPLE SOURCES - USE ALL OF THEM): {{context}}

CRITICAL INSTRUCTION - USE ALL CHUNKS:
- You have MULTIPLE context chunks above (marked as [Source 1], [Source 2], etc.)
- You MUST synthesize information from ALL chunks, not just one
- If multiple chunks mention different methods/tips/ways, include ALL of them
- Synthesize and combine information from ALL chunks into a comprehensive answer
- Do NOT just use the first chunk - use information from ALL relevant chunks

CRITICAL INSTRUCTION: If the question asks about "how to", "ways to", "methods to", "changes", "impacts", "developments", "what happened", or "what are described", you MUST list ALL of them mentioned across ALL context chunks. Do not summarize - extract and list every single method, tip, way, change, fact, development, or detail mentioned. Be exhaustive and comprehensive. Synthesize information from ALL chunks.

IMPORTANT: Answer in {language} language ONLY. The question is in {language}, so your answer must be in {language}.

Provide a clear, comprehensive answer using ONLY information from the context. Extract and synthesize information from ALL context chunks. If multiple chunks mention different methods/tips/ways, include ALL of them. Write naturally in continuous prose sentences, connecting all relevant points from multiple chunks. Do NOT use numbered lists (1., 2., 3.) or bullet points. Be thorough and include all relevant information from ALL chunks. Answer in {language}.""".format(language=lang_name)
        
        return system_prompt, user_template
    
    def generate_answer(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        language: str = 'en',
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate answer using LangChain with universal language support
        
        Args:
            question: User question (any language)
            context_chunks: Retrieved context chunks
            language: Target language code
            
        Returns:
            Generated answer in target language
        """
        if not self.use_langchain or not self.llm:
            # Fallback to simple concatenation
            return self._simple_answer(context_chunks)
        
        # Prepare context
        context_text = self._format_context(context_chunks)
        
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
        
        # Get language-specific prompts
        system_prompt, user_template = self._create_multilingual_prompt(language)
        
        try:
            # Create prompt template with dynamic language support
            prompt = ChatPromptTemplate.from_messages([
                ("system", system_prompt),
                ("user", user_template)
            ])
            
            # Create LangChain chain
            chain = prompt | self.llm | StrOutputParser()
            
            # Generate answer
            answer = chain.invoke({
                "question": question + conversation_context,
                "context": context_text
            })
            
            answer = answer.strip()
            
            # Clean up verbose format (remove structured sections)
            answer = self._clean_answer_format(answer)
            
            return answer
            
        except Exception as e:
            print(f"⚠️  LangChain answer generation failed: {e}")
            import traceback
            traceback.print_exc()
            return self._simple_answer(context_chunks)
    
    def _format_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format context chunks for prompt - improved for better accuracy"""
        context_parts = []
        for i, chunk in enumerate(chunks[:15], 1):  # Increased from 8 to 15 for better coverage
            text = chunk.get('text', '')
            if not text:
                # Try alternative field names
                text = chunk.get('content', '') or chunk.get('chunk_text', '')
            
            if text and text.strip():
                # Increased limit to 2000 chars for better fact extraction
                chunk_text = text[:2000] + "..." if len(text) > 2000 else text
                context_parts.append(f"[Source {i}]: {chunk_text}")
        
        if not context_parts:
            print(f"⚠️  WARNING: No valid text found in chunks for LangChain!")
            print(f"   Chunks: {len(chunks)}")
            print(f"   Sample chunk keys: {list(chunks[0].keys()) if chunks else 'No chunks'}")
        
        return '\n\n'.join(context_parts) if context_parts else "No context available."
    
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
    
    def _simple_answer(self, chunks: List[Dict[str, Any]]) -> str:
        """Simple answer concatenation (fallback)"""
        answer_parts = []
        for chunk in chunks[:3]:
            text = chunk.get('text', '')
            if text:
                answer_parts.append(text)
        
        return ' '.join(answer_parts).strip()


def create_langchain_qa() -> Optional[LangChainRAGQA]:
    """Factory function to create LangChain QA instance"""
    if LANGCHAIN_AVAILABLE and GROQ_AVAILABLE:
        try:
            return LangChainRAGQA(use_langchain=True)
        except Exception as e:
            print(f"⚠️  Failed to create LangChain QA: {e}")
            return None
    return None
