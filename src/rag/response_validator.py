"""
Response Validation for Advanced RAG
Validates answer quality, relevance, and completeness
"""
from typing import Dict, Any, List, Optional
import re

try:
    from groq import Groq
    import os
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class ResponseValidator:
    """
    Validates RAG responses for:
    - Relevance to query
    - Completeness
    - Factual accuracy (grounded in sources)
    - Language consistency
    """
    
    def __init__(self, use_llm: bool = True):
        """
        Initialize response validator
        
        Args:
            use_llm: Use LLM for validation (default: True)
        """
        self.use_llm = use_llm and GROQ_AVAILABLE
        self.groq_client = None
        
        if self.use_llm:
            try:
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    self.groq_client = Groq(api_key=api_key)
                    print("✅ Response validator initialized with Groq")
                else:
                    self.use_llm = False
                    print("⚠️  GROQ_API_KEY not found, using rule-based validation")
            except Exception as e:
                print(f"⚠️  Failed to initialize Groq: {e}")
                self.use_llm = False
    
    def validate(
        self,
        query: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        language: str = 'en'
    ) -> Dict[str, Any]:
        """
        Validate response quality
        
        Args:
            query: Original query
            answer: Generated answer
            retrieved_chunks: Retrieved context chunks
            language: Answer language
            
        Returns:
            Dictionary with:
            - 'is_valid': Boolean
            - 'relevance_score': Float (0-1)
            - 'completeness_score': Float (0-1)
            - 'grounded_score': Float (0-1)
            - 'overall_score': Float (0-1)
            - 'issues': List of issues found
            - 'suggestions': List of improvement suggestions
        """
        if self.use_llm and self.groq_client:
            return self._validate_with_llm(query, answer, retrieved_chunks, language)
        else:
            return self._validate_rule_based(query, answer, retrieved_chunks, language)
    
    def _validate_with_llm(
        self,
        query: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        """Validate using LLM"""
        try:
            # Prepare context
            context = '\n\n'.join([chunk.get('text', '')[:500] for chunk in retrieved_chunks[:3]])
            
            prompt = f"""Evaluate the quality of this answer to the given question.

Question: {query}
Answer: {answer}
Context (sources): {context[:1000]}

Evaluate on:
1. Relevance (0-1): Does the answer address the question?
2. Completeness (0-1): Is the answer complete and informative?
3. Groundedness (0-1): Is the answer supported by the context?

Provide scores and any issues or suggestions.
Format:
RELEVANCE: [score]
COMPLETENESS: [score]
GROUNDED: [score]
ISSUES: [list of issues, or "None"]
SUGGESTIONS: [list of suggestions, or "None"]"""

            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a response quality evaluator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=300
            )
            
            text = response.choices[0].message.content
            
            # Parse response
            relevance = 0.5
            completeness = 0.5
            grounded = 0.5
            issues = []
            suggestions = []
            
            if "RELEVANCE:" in text:
                try:
                    relevance = float(text.split("RELEVANCE:")[1].split()[0])
                except:
                    pass
            
            if "COMPLETENESS:" in text:
                try:
                    completeness = float(text.split("COMPLETENESS:")[1].split()[0])
                except:
                    pass
            
            if "GROUNDED:" in text:
                try:
                    grounded = float(text.split("GROUNDED:")[1].split()[0])
                except:
                    pass
            
            if "ISSUES:" in text:
                issues_text = text.split("ISSUES:")[1].split("SUGGESTIONS:")[0].strip()
                if issues_text.lower() != "none":
                    issues = [i.strip() for i in issues_text.split(',') if i.strip()]
            
            if "SUGGESTIONS:" in text:
                suggestions_text = text.split("SUGGESTIONS:")[1].strip()
                if suggestions_text.lower() != "none":
                    suggestions = [s.strip() for s in suggestions_text.split(',') if s.strip()]
            
            overall = (relevance + completeness + grounded) / 3.0
            
            return {
                'is_valid': overall >= 0.5,
                'relevance_score': relevance,
                'completeness_score': completeness,
                'grounded_score': grounded,
                'overall_score': overall,
                'issues': issues,
                'suggestions': suggestions,
                'method': 'llm'
            }
            
        except Exception as e:
            print(f"⚠️  LLM validation failed: {e}")
            return self._validate_rule_based(query, answer, retrieved_chunks, language)
    
    def _validate_rule_based(
        self,
        query: str,
        answer: str,
        retrieved_chunks: List[Dict[str, Any]],
        language: str
    ) -> Dict[str, Any]:
        """Rule-based validation"""
        issues = []
        suggestions = []
        
        # 1. Relevance: Check if answer contains query keywords
        query_keywords = set(re.findall(r'\b\w+\b', query.lower()))
        answer_keywords = set(re.findall(r'\b\w+\b', answer.lower()))
        overlap = len(query_keywords & answer_keywords)
        relevance = min(overlap / len(query_keywords) if query_keywords else 0, 1.0)
        
        if relevance < 0.3:
            issues.append("Answer may not be relevant to the question")
        
        # 2. Completeness: Check answer length and structure
        answer_length = len(answer.split())
        completeness = min(answer_length / 50.0, 1.0)  # Expect at least 50 words
        
        if completeness < 0.5:
            issues.append("Answer may be too short or incomplete")
            suggestions.append("Consider providing more detail")
        
        # 3. Groundedness: Check if answer relates to retrieved chunks
        chunk_texts = ' '.join([chunk.get('text', '') for chunk in retrieved_chunks])
        chunk_keywords = set(re.findall(r'\b\w+\b', chunk_texts.lower()))
        answer_chunk_overlap = len(answer_keywords & chunk_keywords)
        grounded = min(answer_chunk_overlap / len(answer_keywords) if answer_keywords else 0, 1.0)
        
        if grounded < 0.3:
            issues.append("Answer may not be well-grounded in sources")
            suggestions.append("Verify answer is supported by retrieved context")
        
        # 4. Language consistency
        if language != 'en':
            # Simple check: answer should contain non-ASCII if query does
            query_has_non_ascii = any(ord(c) > 127 for c in query)
            answer_has_non_ascii = any(ord(c) > 127 for c in answer)
            if query_has_non_ascii and not answer_has_non_ascii:
                issues.append("Answer language may not match query language")
        
        overall = (relevance + completeness + grounded) / 3.0
        
        return {
            'is_valid': overall >= 0.5,
            'relevance_score': relevance,
            'completeness_score': completeness,
            'grounded_score': grounded,
            'overall_score': overall,
            'issues': issues,
            'suggestions': suggestions,
            'method': 'rule_based'
        }
