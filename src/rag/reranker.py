"""
Cross-Encoder Re-ranking for Advanced RAG
Re-ranks retrieved results using cross-encoder models for better precision
"""
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

try:
    from sentence_transformers import CrossEncoder
    CROSS_ENCODER_AVAILABLE = True
except ImportError:
    CROSS_ENCODER_AVAILABLE = False
    CrossEncoder = None


class ReRanker:
    """
    Cross-encoder re-ranker for better result precision
    Uses cross-encoder models that score query-document pairs directly
    """
    
    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Fast, good quality
    ALTERNATIVE_MODELS = [
        "cross-encoder/ms-marco-MiniLM-L-12-v2",  # Better quality, slower
        "cross-encoder/ms-marco-electra-base",  # Best quality
    ]
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize re-ranker
        
        Args:
            model_name: Cross-encoder model name
        """
        self.model_name = model_name or self.DEFAULT_MODEL
        self.model = None
        
        if CROSS_ENCODER_AVAILABLE:
            self._load_model()
        else:
            print("⚠️  sentence-transformers not available, re-ranking disabled")
    
    def _load_model(self):
        """Load cross-encoder model"""
        try:
            print(f"Loading re-ranker model: {self.model_name}")
            self.model = CrossEncoder(self.model_name)
            print(f"✅ Re-ranker model loaded successfully")
        except Exception as e:
            print(f"⚠️  Failed to load {self.model_name}: {e}")
            # Try alternatives
            for alt_model in self.ALTERNATIVE_MODELS:
                try:
                    print(f"Trying alternative model: {alt_model}")
                    self.model = CrossEncoder(alt_model)
                    self.model_name = alt_model
                    print(f"✅ Re-ranker model {alt_model} loaded successfully")
                    break
                except Exception:
                    continue
            
            if self.model is None:
                print("⚠️  Re-ranking disabled - no model available")
    
    def rerank(
        self,
        query: str,
        results: List[Tuple[Dict[str, Any], float]],
        top_k: Optional[int] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Re-rank results using cross-encoder
        
        Args:
            query: Original query
            results: List of (metadata, original_score) tuples
            top_k: Number of top results to return (None = all)
            
        Returns:
            Re-ranked list of (metadata, reranked_score) tuples
        """
        if not self.model or not results:
            return results
        
        if top_k is None:
            top_k = len(results)
        
        # Prepare query-document pairs
        pairs = []
        for meta, _ in results:
            text = meta.get('text', '')
            pairs.append([query, text])
        
        # Score pairs
        try:
            scores = self.model.predict(pairs)
            
            # Combine with original scores (weighted average)
            reranked = []
            for i, (meta, original_score) in enumerate(results):
                rerank_score = float(scores[i])
                # Combine: 70% rerank score, 30% original score
                combined_score = 0.7 * rerank_score + 0.3 * original_score
                reranked.append((meta, combined_score))
            
            # Sort by combined score
            reranked.sort(key=lambda x: x[1], reverse=True)
            
            return reranked[:top_k]
            
        except Exception as e:
            print(f"⚠️  Re-ranking failed: {e}")
            return results  # Return original results on error
    
    def is_available(self) -> bool:
        """Check if re-ranker is available"""
        return self.model is not None
