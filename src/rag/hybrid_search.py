"""
Hybrid Search: Combines Semantic (Vector) and Keyword (BM25) Search
Better retrieval by leveraging both semantic understanding and exact keyword matching
"""
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from collections import Counter
import math

from src.rag.embeddings import MultilingualEmbedder
from src.rag.vectorstore import FAISSVectorStore
from src.memory import StorageService


class HybridSearch:
    """
    Hybrid search combining:
    1. Semantic search (vector embeddings)
    2. Keyword search (BM25-like scoring)
    """
    
    def __init__(
        self,
        embedder: MultilingualEmbedder,
        vectorstore: FAISSVectorStore,
        storage_service: StorageService,
        user_id: int
    ):
        """
        Initialize hybrid search
        
        Args:
            embedder: Embedding generator
            vectorstore: FAISS vector store
            storage_service: Storage service for accessing transcripts
            user_id: User ID for isolation
        """
        self.embedder = embedder
        self.vectorstore = vectorstore
        self.storage_service = storage_service
        self.user_id = user_id
        
        # BM25 parameters
        self.k1 = 1.5  # Term frequency saturation parameter
        self.b = 0.75  # Length normalization parameter
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization"""
        import re
        # Remove punctuation and split
        tokens = re.findall(r'\b\w+\b', text.lower())
        return tokens
    
    def _compute_bm25_score(
        self,
        query_tokens: List[str],
        doc_tokens: List[str],
        doc_freq: Dict[str, int],
        avg_doc_length: float,
        total_docs: int
    ) -> float:
        """
        Compute BM25 score for a document
        
        Args:
            query_tokens: Query tokens
            doc_tokens: Document tokens
            doc_freq: Document frequency of terms
            avg_doc_length: Average document length
            total_docs: Total number of documents
            
        Returns:
            BM25 score
        """
        score = 0.0
        doc_length = len(doc_tokens)
        doc_token_counts = Counter(doc_tokens)
        
        for term in query_tokens:
            if term not in doc_tokens:
                continue
            
            # Term frequency in document
            tf = doc_token_counts[term]
            
            # Inverse document frequency
            df = doc_freq.get(term, 1)
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1.0)
            
            # BM25 formula
            numerator = idf * tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_length / avg_doc_length))
            
            score += numerator / denominator
        
        return score
    
    def search(
        self,
        query: str,
        top_k: int = 10,
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3,
        min_score: float = 0.0
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Hybrid search combining semantic and keyword search
        
        Args:
            query: Search query
            top_k: Number of results to return
            semantic_weight: Weight for semantic search (0-1)
            keyword_weight: Weight for keyword search (0-1)
            min_score: Minimum combined score
            
        Returns:
            List of (metadata, combined_score) tuples, sorted by score
        """
        # Normalize weights
        total_weight = semantic_weight + keyword_weight
        if total_weight > 0:
            semantic_weight /= total_weight
            keyword_weight /= total_weight
        
        # 1. Semantic search
        query_embedding = self.embedder.embed_text(query)
        semantic_results = self.vectorstore.search(
            query_embedding=query_embedding,
            k=top_k * 2  # Get more for re-ranking
        )
        
        # 2. Keyword search
        keyword_results = self._keyword_search(query, top_k * 2)
        
        # Combine results
        combined_scores = {}
        
        # Add semantic scores
        max_semantic = max([score for _, score in semantic_results], default=1.0)
        for meta, score in semantic_results:
            key = self._get_result_key(meta)
            normalized_score = score / max_semantic if max_semantic > 0 else 0
            combined_scores[key] = {
                'metadata': meta,
                'semantic_score': normalized_score,
                'keyword_score': 0.0
            }
        
        # Add keyword scores
        max_keyword = max([score for _, score in keyword_results], default=1.0)
        for meta, score in keyword_results:
            key = self._get_result_key(meta)
            normalized_score = score / max_keyword if max_keyword > 0 else 0
            if key in combined_scores:
                combined_scores[key]['keyword_score'] = normalized_score
            else:
                combined_scores[key] = {
                    'metadata': meta,
                    'semantic_score': 0.0,
                    'keyword_score': normalized_score
                }
        
        # Compute combined scores
        final_results = []
        for key, data in combined_scores.items():
            combined_score = (
                semantic_weight * data['semantic_score'] +
                keyword_weight * data['keyword_score']
            )
            
            if combined_score >= min_score:
                final_results.append((data['metadata'], combined_score))
        
        # Sort by combined score
        final_results.sort(key=lambda x: x[1], reverse=True)
        
        return final_results[:top_k]
    
    def _keyword_search(self, query: str, top_k: int) -> List[Tuple[Dict[str, Any], float]]:
        """Perform keyword-based search using BM25"""
        query_tokens = self._tokenize(query)
        
        if not query_tokens:
            return []
        
        # Get all user transcripts for BM25 calculation
        transcripts = self.storage_service.get_user_transcripts(
            user_id=self.user_id,
            limit=10000
        )
        
        if not transcripts:
            return []
        
        # Build document frequency and tokenize all documents
        all_docs = []
        doc_freq = Counter()
        
        for transcript in transcripts:
            text = transcript.get('text', '')
            tokens = self._tokenize(text)
            all_docs.append({
                'metadata': transcript,
                'tokens': tokens
            })
            doc_freq.update(set(tokens))
        
        # Calculate average document length
        avg_doc_length = sum(len(doc['tokens']) for doc in all_docs) / len(all_docs) if all_docs else 1.0
        
        # Score each document
        scored_docs = []
        for doc in all_docs:
            score = self._compute_bm25_score(
                query_tokens=query_tokens,
                doc_tokens=doc['tokens'],
                doc_freq=doc_freq,
                avg_doc_length=avg_doc_length,
                total_docs=len(all_docs)
            )
            
            if score > 0:
                # Convert transcript to chunk metadata format
                metadata = {
                    'text': doc['metadata'].get('text', ''),
                    'transcript_id': doc['metadata'].get('id'),
                    'document_id': doc['metadata'].get('document_id'),
                    'type': 'paragraph',
                    'language': doc['metadata'].get('language', 'en'),
                    'start': None,
                    'end': None
                }
                scored_docs.append((metadata, score))
        
        # Sort by score
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        return scored_docs[:top_k]
    
    def _get_result_key(self, metadata: Dict[str, Any]) -> str:
        """Generate unique key for a result"""
        transcript_id = metadata.get('transcript_id', '')
        start = metadata.get('start', '')
        end = metadata.get('end', '')
        return f"{transcript_id}_{start}_{end}"
