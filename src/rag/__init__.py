"""
Advanced RAG (Retrieval-Augmented Generation) module
Multilingual semantic search and question-answering with:
- Query rewriting
- Hybrid search (semantic + keyword)
- Re-ranking
- Response validation
- Answer refinement
"""
try:
    from src.rag.embeddings import MultilingualEmbedder
    from src.rag.vectorstore import FAISSVectorStore
    from src.rag.qa import RAGQAEngine
    from src.rag.query_rewriter import QueryRewriter
    from src.rag.hybrid_search import HybridSearch
    from src.rag.reranker import ReRanker
    from src.rag.response_validator import ResponseValidator
    from src.rag.answer_refiner import AnswerRefiner
    __all__ = [
        'MultilingualEmbedder',
        'FAISSVectorStore',
        'RAGQAEngine',
        'QueryRewriter',
        'HybridSearch',
        'ReRanker',
        'ResponseValidator',
        'AnswerRefiner'
    ]
except ImportError as e:
    # Handle missing dependencies gracefully
    print(f"Warning: RAG module dependencies not available: {e}")
    __all__ = []
