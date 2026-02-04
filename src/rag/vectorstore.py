"""
FAISS vector store with per-user isolation
Stores embeddings for semantic search
"""
import os
import pickle
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from pathlib import Path

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None

from src.core.config import Config


class FAISSVectorStore:
    """
    FAISS-based vector store with per-user isolation
    Each user has their own vector index
    """
    
    def __init__(self, user_id: int, embedding_dim: int = 384):
        """
        Initialize FAISS vector store for a user
        
        Args:
            user_id: User ID for isolation
            embedding_dim: Dimension of embeddings (default: 384 for MiniLM)
        """
        if not FAISS_AVAILABLE:
            raise ImportError(
                "faiss-cpu is required for vector store. "
                "Install with: pip install faiss-cpu"
            )
        
        self.user_id = user_id
        self.embedding_dim = embedding_dim
        
        # Create user-specific directory
        self.store_dir = Config.DATA_DIR / "vectorstores" / f"user_{user_id}"
        self.store_dir.mkdir(parents=True, exist_ok=True)
        
        # Index file paths
        self.index_file = self.store_dir / "index.faiss"
        self.metadata_file = self.store_dir / "metadata.pkl"
        
        # Initialize FAISS index (L2 distance for cosine similarity)
        # Using IndexFlatIP (Inner Product) for cosine similarity
        # Normalize vectors for cosine similarity
        self.index = faiss.IndexFlatIP(embedding_dim)  # Inner product for normalized vectors
        
        # Metadata storage: list of dicts, one per vector
        self.metadata: List[Dict[str, Any]] = []
        
        # Load existing index if available
        self._load_index()
    
    def _load_index(self):
        """Load existing FAISS index and metadata"""
        if self.index_file.exists() and self.metadata_file.exists():
            try:
                # Load FAISS index
                self.index = faiss.read_index(str(self.index_file))
                
                # Load metadata
                with open(self.metadata_file, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                print(f"✅ Loaded vector store for user {self.user_id}: {len(self.metadata)} vectors")
            except Exception as e:
                print(f"⚠️  Failed to load existing index: {e}. Creating new index.")
                self.index = faiss.IndexFlatIP(self.embedding_dim)
                self.metadata = []
    
    def _save_index(self):
        """Save FAISS index and metadata to disk"""
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_file))
            
            # Save metadata
            with open(self.metadata_file, 'wb') as f:
                pickle.dump(self.metadata, f)
        except Exception as e:
            print(f"⚠️  Failed to save index: {e}")
    
    def _normalize_vectors(self, vectors: np.ndarray) -> np.ndarray:
        """Normalize vectors for cosine similarity"""
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1  # Avoid division by zero
        return vectors / norms
    
    def add_embeddings(
        self,
        embeddings: np.ndarray,
        metadata: List[Dict[str, Any]]
    ):
        """
        Add embeddings to the vector store
        
        Args:
            embeddings: Embedding vectors (numpy array, shape: [num_vectors, embedding_dim])
            metadata: List of metadata dicts (one per vector)
                     Should include: 'text', 'transcript_id', 'document_id', 'start', 'end', etc.
        """
        if len(embeddings) != len(metadata):
            raise ValueError("Number of embeddings must match number of metadata entries")
        
        if embeddings.shape[1] != self.embedding_dim:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.embedding_dim}, "
                f"got {embeddings.shape[1]}"
            )
        
        # Normalize vectors for cosine similarity
        normalized = self._normalize_vectors(embeddings)
        
        # Add to FAISS index
        self.index.add(normalized.astype('float32'))
        
        # Add metadata
        self.metadata.extend(metadata)
        
        # Save to disk
        self._save_index()
        
        print(f"✅ Added {len(embeddings)} vectors to store for user {self.user_id}")
    
    def search(
        self,
        query_embedding: np.ndarray,
        k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[Dict[str, Any], float]]:
        """
        Search for similar vectors
        
        Args:
            query_embedding: Query embedding vector (shape: [embedding_dim])
            k: Number of results to return
            filter_dict: Optional filter criteria (e.g., {'transcript_id': 123})
            
        Returns:
            List of tuples: (metadata_dict, similarity_score)
            Results sorted by similarity (highest first)
        """
        if self.index.ntotal == 0:
            return []
        
        # Normalize query vector
        query_norm = query_embedding / (np.linalg.norm(query_embedding) or 1.0)
        query_norm = query_norm.reshape(1, -1).astype('float32')
        
        # Search in FAISS
        k = min(k, self.index.ntotal)  # Don't request more than available
        distances, indices = self.index.search(query_norm, k)
        
        # Get results with metadata
        results = []
        for idx, dist in zip(indices[0], distances[0]):
            if idx < 0:  # FAISS returns -1 for invalid indices
                continue
            
            metadata = self.metadata[idx].copy()
            
            # Apply filters if specified
            if filter_dict:
                match = True
                for key, value in filter_dict.items():
                    if metadata.get(key) != value:
                        match = False
                        break
                if not match:
                    continue
            
            # Convert distance to similarity (for Inner Product, higher is better)
            similarity = float(dist)
            results.append((metadata, similarity))
        
        # Sort by similarity (descending)
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results
    
    def delete_by_transcript(self, transcript_id: int):
        """
        Delete all vectors associated with a transcript
        Note: FAISS doesn't support deletion, so we rebuild the index
        
        Args:
            transcript_id: Transcript ID to remove
        """
        # Filter out metadata for this transcript
        original_count = len(self.metadata)
        self.metadata = [
            m for m in self.metadata
            if m.get('transcript_id') != transcript_id
        ]
        
        removed_count = original_count - len(self.metadata)
        
        if removed_count > 0:
            # Rebuild index without deleted vectors
            if len(self.metadata) > 0:
                # Re-extract embeddings would be needed, but we don't store them
                # For now, just clear and let re-indexing happen
                self.index = faiss.IndexFlatIP(self.embedding_dim)
                print(f"⚠️  Removed {removed_count} vectors for transcript {transcript_id}. "
                      f"Re-indexing required.")
            else:
                self.index = faiss.IndexFlatIP(self.embedding_dim)
            
            self._save_index()
    
    def get_indexed_transcript_ids(self) -> set:
        """Get set of transcript IDs that are already indexed"""
        transcript_ids = set()
        for meta in self.metadata:
            tid = meta.get('transcript_id')
            if tid:
                transcript_ids.add(tid)
        return transcript_ids
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store"""
        indexed_transcripts = self.get_indexed_transcript_ids()
        return {
            'user_id': self.user_id,
            'num_vectors': self.index.ntotal,
            'embedding_dim': self.embedding_dim,
            'store_dir': str(self.store_dir),
            'indexed_transcript_count': len(indexed_transcripts),
            'indexed_transcript_ids': list(indexed_transcripts)
        }
    
    def clear(self):
        """Clear all vectors (use with caution)"""
        # Delete index files from disk
        try:
            if self.index_file.exists():
                self.index_file.unlink()
                print(f"✅ Deleted index file: {self.index_file}")
            if self.metadata_file.exists():
                self.metadata_file.unlink()
                print(f"✅ Deleted metadata file: {self.metadata_file}")
        except Exception as e:
            print(f"⚠️  Failed to delete index files: {e}")
        
        # Reset in-memory index and metadata
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.metadata = []
        
        # Save empty index to ensure consistency
        self._save_index()
        print(f"✅ Cleared vector store for user {self.user_id}")
    
    def delete_all(self):
        """Delete all embeddings (alias for clear)"""
        self.clear()
