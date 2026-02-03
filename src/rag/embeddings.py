"""
Multilingual embeddings pipeline using Sentence Transformers
Supports cross-lingual semantic search
"""
import os
from typing import List, Optional, Dict, Any
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None


class MultilingualEmbedder:
    """
    Multilingual embedding generator using Sentence Transformers
    Supports queries in any language, retrieves content in any language
    """
    
    # Recommended multilingual models (free, open-source)
    # These models support 100+ languages
    DEFAULT_MODEL = "paraphrase-multilingual-MiniLM-L12-v2"  # Fast, good quality
    ALTERNATIVE_MODELS = [
        "paraphrase-multilingual-mpnet-base-v2",  # Better quality, slower
        "multilingual-e5-base",  # Excellent quality
    ]
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize multilingual embedder
        
        Args:
            model_name: Name of Sentence Transformer model (defaults to DEFAULT_MODEL)
        """
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError(
                "sentence-transformers is required for RAG. "
                "Install with: pip install sentence-transformers"
            )
        
        self.model_name = model_name or self.DEFAULT_MODEL
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the Sentence Transformer model"""
        try:
            print(f"Loading multilingual embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            print(f"✅ Model {self.model_name} loaded successfully")
        except Exception as e:
            print(f"⚠️  Failed to load {self.model_name}: {e}")
            # Try alternative models
            for alt_model in self.ALTERNATIVE_MODELS:
                try:
                    print(f"Trying alternative model: {alt_model}")
                    self.model = SentenceTransformer(alt_model)
                    self.model_name = alt_model
                    print(f"✅ Model {alt_model} loaded successfully")
                    break
                except Exception:
                    continue
            
            if self.model is None:
                raise RuntimeError(
                    f"Failed to load any multilingual embedding model. "
                    f"Tried: {self.model_name}, {', '.join(self.ALTERNATIVE_MODELS)}"
                )
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for a single text
        
        Args:
            text: Input text (any language)
            
        Returns:
            Embedding vector (numpy array)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        # Handle empty text
        if not text or not text.strip():
            # Return zero vector with correct dimension
            return np.zeros(self.model.get_sentence_embedding_dimension())
        
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding
    
    def embed_batch(self, texts: List[str], batch_size: int = 64, show_progress: bool = False) -> np.ndarray:
        """
        Generate embeddings for multiple texts (batch processing)
        
        Args:
            texts: List of input texts (any languages)
            batch_size: Batch size for processing
            show_progress: Show progress bar
            
        Returns:
            Embedding matrix (numpy array, shape: [num_texts, embedding_dim])
        """
        if self.model is None:
            raise RuntimeError("Model not loaded")
        
        if not texts:
            return np.array([])
        
        # Filter empty texts
        non_empty_texts = [t if t and t.strip() else " " for t in texts]
        
        embeddings = self.model.encode(
            non_empty_texts,
            batch_size=batch_size,
            show_progress_bar=show_progress,
            convert_to_numpy=True
        )
        
        return embeddings
    
    def embed_paragraphs(self, paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate embeddings for paragraph-level data
        
        Args:
            paragraphs: List of paragraph dicts with 'text' key
                       Can include metadata like 'start', 'end', 'transcript_id'
            
        Returns:
            List of paragraph dicts with added 'embedding' key
        """
        texts = [p.get('text', '') for p in paragraphs]
        embeddings = self.embed_batch(texts)
        
        # Add embeddings to paragraphs
        result = []
        for i, para in enumerate(paragraphs):
            para_copy = para.copy()
            para_copy['embedding'] = embeddings[i]
            result.append(para_copy)
        
        return result
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings"""
        if self.model is None:
            raise RuntimeError("Model not loaded")
        return self.model.get_sentence_embedding_dimension()
    
    def detect_language(self, text: str) -> str:
        """
        Simple language detection based on character patterns
        For more accurate detection, use langdetect library
        
        Args:
            text: Input text
            
        Returns:
            Language code (e.g., 'en', 'hi', 'te')
        """
        # Simple heuristic-based detection
        # For production, use langdetect or similar
        if not text:
            return 'en'
        
        # Check for Devanagari script (Hindi, Marathi, etc.)
        if any('\u0900' <= char <= '\u097F' for char in text):
            return 'hi'
        
        # Check for Telugu script
        if any('\u0C00' <= char <= '\u0C7F' for char in text):
            return 'te'
        
        # Check for Tamil script
        if any('\u0B80' <= char <= '\u0BFF' for char in text):
            return 'ta'
        
        # Default to English
        return 'en'
