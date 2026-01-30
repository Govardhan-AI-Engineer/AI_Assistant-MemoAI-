"""
Query Rewriting for Advanced RAG
Improves query quality for better retrieval
"""
from typing import Optional, List, Dict, Any
import re

try:
    from groq import Groq
    import os
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False


class QueryRewriter:
    """
    Query rewriting to improve retrieval quality
    - Expands queries with synonyms
    - Reformulates questions for better semantic matching
    - Handles multilingual queries
    """
    
    def __init__(self, use_llm: bool = True):
        """
        Initialize query rewriter
        
        Args:
            use_llm: Use LLM for query expansion (default: True)
        """
        self.use_llm = use_llm and GROQ_AVAILABLE
        self.groq_client = None
        
        if self.use_llm:
            try:
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    self.groq_client = Groq(api_key=api_key)
                    print("✅ Query rewriter initialized with Groq")
                else:
                    self.use_llm = False
                    print("⚠️  GROQ_API_KEY not found, using rule-based rewriting")
            except Exception as e:
                print(f"⚠️  Failed to initialize Groq: {e}")
                self.use_llm = False
    
    def rewrite_query(self, query: str, language: str = 'en') -> Dict[str, Any]:
        """
        Rewrite query to improve retrieval
        
        Args:
            query: Original query
            language: Query language
            
        Returns:
            Dictionary with:
            - 'original': Original query
            - 'rewritten': Rewritten query
            - 'expanded': Expanded query with synonyms
            - 'keywords': Extracted keywords
            - 'method': Rewriting method used
        """
        original = query.strip()
        
        # Extract keywords
        keywords = self._extract_keywords(original)
        
        if self.use_llm and self.groq_client:
            # Use LLM for query rewriting
            rewritten, expanded = self._rewrite_with_llm(original, language)
            method = 'llm'
        else:
            # Rule-based rewriting
            rewritten = self._rewrite_rule_based(original)
            expanded = self._expand_rule_based(original, keywords)
            method = 'rule_based'
        
        return {
            'original': original,
            'rewritten': rewritten,
            'expanded': expanded,
            'keywords': keywords,
            'method': method
        }
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from query"""
        # Remove common stop words (basic list)
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'what', 'when', 'where',
            'who', 'why', 'how', 'this', 'that', 'these', 'those'
        }
        
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def _rewrite_with_llm(self, query: str, language: str) -> tuple:
        """Rewrite query using LLM"""
        try:
            # Create prompt for query rewriting
            prompt = f"""Rewrite the following question to improve information retrieval. 
Make it more specific and search-friendly while preserving the original intent.

Original question: {query}
Language: {language}

Provide:
1. A rewritten version (more specific, better for search)
2. An expanded version (with synonyms and related terms)

Format:
REWRITTEN: [rewritten query]
EXPANDED: [expanded query with synonyms]"""

            response = self.groq_client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": "You are a query rewriting assistant. Rewrite questions to improve search quality."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            text = response.choices[0].message.content
            
            # Parse response
            rewritten = query  # Fallback
            expanded = query   # Fallback
            
            if "REWRITTEN:" in text:
                rewritten = text.split("REWRITTEN:")[1].split("EXPANDED:")[0].strip()
            if "EXPANDED:" in text:
                expanded = text.split("EXPANDED:")[1].strip()
            
            return rewritten, expanded
            
        except Exception as e:
            print(f"⚠️  LLM rewriting failed: {e}")
            return self._rewrite_rule_based(query), self._expand_rule_based(query, self._extract_keywords(query))
    
    def _rewrite_rule_based(self, query: str) -> str:
        """Rule-based query rewriting"""
        # Remove question words at start if they don't add value
        query = re.sub(r'^(what|when|where|who|why|how)\s+', '', query, flags=re.IGNORECASE)
        
        # Expand contractions
        contractions = {
            "what's": "what is",
            "who's": "who is",
            "where's": "where is",
            "it's": "it is",
            "that's": "that is"
        }
        for cont, exp in contractions.items():
            query = query.replace(cont, exp)
        
        # Ensure query ends properly
        if not query.endswith(('?', '.', '!')):
            query = query.strip()
        
        return query
    
    def _expand_rule_based(self, query: str, keywords: List[str]) -> str:
        """Rule-based query expansion with synonyms"""
        # Basic synonym expansion (can be enhanced)
        synonyms = {
            'ai': ['artificial intelligence', 'machine learning', 'ML'],
            'discuss': ['talk', 'mention', 'say', 'speak'],
            'important': ['significant', 'key', 'main', 'crucial'],
            'explain': ['describe', 'clarify', 'detail', 'elaborate']
        }
        
        expanded_terms = []
        for keyword in keywords:
            expanded_terms.append(keyword)
            if keyword in synonyms:
                expanded_terms.extend(synonyms[keyword])
        
        # Combine original query with expanded terms
        if expanded_terms:
            expanded = f"{query} {' '.join(set(expanded_terms))}"
        else:
            expanded = query
        
        return expanded
    
    def generate_search_queries(self, query: str, language: str = 'en', num_variants: int = 3) -> List[str]:
        """
        Generate multiple query variants for better retrieval
        
        Args:
            query: Original query
            language: Query language
            num_variants: Number of variants to generate
            
        Returns:
            List of query variants
        """
        rewritten = self.rewrite_query(query, language)
        
        variants = [
            rewritten['original'],
            rewritten['rewritten'],
            rewritten['expanded']
        ]
        
        # Add keyword-based variants
        if rewritten['keywords']:
            variants.append(' '.join(rewritten['keywords']))
        
        # Remove duplicates and limit
        unique_variants = []
        seen = set()
        for v in variants:
            if v and v.lower() not in seen:
                unique_variants.append(v)
                seen.add(v.lower())
        
        return unique_variants[:num_variants]
