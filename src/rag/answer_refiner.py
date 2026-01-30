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
    """
    
    def __init__(self, use_llm: bool = True):
        """
        Initialize answer refiner
        
        Args:
            use_llm: Use LLM for refinement (default: True)
        """
        self.use_llm = use_llm and GROQ_AVAILABLE
        self.groq_client = None
        
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
        min_relevance: float = 0.3
    ) -> Dict[str, Any]:
        """
        Refine answer using LLM
        
        Args:
            question: User question
            retrieved_chunks: Retrieved context chunks
            language: Target language
            max_length: Maximum answer length
            min_relevance: Minimum relevance threshold for using context
            
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
            result = self._refine_with_llm(question, retrieved_chunks, language, max_length)
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
        """Check if retrieved context is relevant to the question"""
        if not retrieved_chunks:
            return False
        
        # Handle very short queries (greetings, etc.) - treat as general knowledge
        question_lower = question.lower().strip()
        short_greetings = {'hi', 'hey', 'hello', 'bye', 'thanks', 'thank you', 'ok', 'okay', 'yes', 'no'}
        
        # If it's a very short query or a greeting, don't use context
        if len(question_lower) <= 3 or question_lower in short_greetings:
            return False
        
        # Simple relevance check: see if question keywords appear in chunks
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
        max_length: int
    ) -> Dict[str, Any]:
        """Refine answer using LLM"""
        try:
            # Prepare context from top chunks
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks[:5]):  # Use top 5 chunks
                text = chunk.get('text', '')
                if text:
                    context_parts.append(f"[Source {i+1}]: {text[:300]}")  # Limit each chunk
            
            context = '\n\n'.join(context_parts)
            
            # Create prompt
            language_instruction = f"Answer in {language} language." if language != 'en' else ""
            
            prompt = f"""You are answering questions based ONLY on the provided context from the user's stored transcripts.
{language_instruction}

CRITICAL RULES:
1. Answer STRICTLY using only information from the provided context
2. Do NOT use any external knowledge or general information
3. If the context doesn't contain enough information to answer the question, say: "I cannot find enough information in your stored transcripts to answer this question."
4. Ground your answer in the provided context
5. Be concise and clear

Question: {question}

Context from user's transcripts:
{context}

Provide a clear, well-structured answer based ONLY on the context above (max {max_length} words):"""

            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that answers questions based on provided context. Always cite sources when possible."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=min(max_length * 2, 1000)  # Rough token estimate
            )
            
            refined_answer = response.choices[0].message.content.strip()
            
            return {
                'refined_answer': refined_answer,
                'method': 'llm',
                'chunks_used': min(len(retrieved_chunks), 5),
                'is_from_context': True,
                'context_relevant': True
            }
            
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
                'hello': 'नमस्ते! आप अपनी ट्रांसक्रिप्ट के बारे में क्या जानना चाहेंगे?'
            },
            'te': {
                'hi': 'నమస్కారం! మీ ట్రాన్స్క్రిప్ట్‌ల గురించి నేను ఎలా సహాయం చేయగలను?',
                'hey': 'నమస్కారం! నేను ఎలా సహాయం చేయగలను?',
                'hello': 'నమస్కారం! మీ ట్రాన్స్క్రిప్ట్‌ల గురించి మీరు ఏమి తెలుసుకోవాలనుకుంటున్నారు?'
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
                'answer': 'I cannot answer this question as it is not related to your stored transcripts. Please ask questions about your uploaded content.',
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
                'answer': 'I cannot answer this question as it is not related to your stored transcripts. Please ask questions about your uploaded content.',
                'method': 'fallback',
                'is_from_context': False
            }
