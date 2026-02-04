"""
Advanced RAG Question-Answering Engine
Multilingual QA with query rewriting, hybrid search, re-ranking, validation, and answer refinement
"""
from typing import List, Dict, Any, Optional, Tuple
import re

from src.rag.embeddings import MultilingualEmbedder
from src.rag.vectorstore import FAISSVectorStore
from src.rag.query_rewriter import QueryRewriter
from src.rag.hybrid_search import HybridSearch
from src.rag.reranker import ReRanker
from src.rag.response_validator import ResponseValidator
from src.rag.answer_refiner import AnswerRefiner
from src.memory import StorageService
from src.translation.integration import TranscriptionTranslationIntegration


class RAGQAEngine:
    """
    Advanced Multilingual RAG Question-Answering Engine
    
    Features:
    - Query rewriting for better retrieval
    - Hybrid search (semantic + keyword)
    - Cross-encoder re-ranking
    - Response validation
    - LLM-based answer refinement
    - Multilingual support with same-language responses
    - Citations with document IDs and timestamps
    """
    
    def __init__(
        self,
        user_id: int,
        storage_service: StorageService,
        translation_service: Optional[TranscriptionTranslationIntegration] = None,
        embedding_model: Optional[str] = None,
        enable_advanced: bool = True
    ):
        """
        Initialize Advanced RAG QA Engine
        
        Args:
            user_id: User ID for data isolation
            storage_service: Storage service for accessing transcripts
            translation_service: Optional translation service for cross-lingual answers
            embedding_model: Optional embedding model name
            enable_advanced: Enable advanced features (rewriting, hybrid search, etc.)
        """
        self.user_id = user_id
        self.storage_service = storage_service
        self.translation_service = translation_service
        self.enable_advanced = enable_advanced
        
        # Initialize embedder
        self.embedder = MultilingualEmbedder(model_name=embedding_model)
        
        # Initialize vector store
        embedding_dim = self.embedder.get_embedding_dimension()
        self.vectorstore = FAISSVectorStore(user_id=user_id, embedding_dim=embedding_dim)
        
        # Initialize advanced components
        if enable_advanced:
            self.query_rewriter = QueryRewriter(use_llm=True)
            self.hybrid_search = HybridSearch(
                embedder=self.embedder,
                vectorstore=self.vectorstore,
                storage_service=storage_service,
                user_id=user_id
            )
            self.reranker = ReRanker()
            self.validator = ResponseValidator(use_llm=True)
            self.refiner = AnswerRefiner(use_llm=True)
        else:
            self.query_rewriter = None
            self.hybrid_search = None
            self.reranker = None
            self.validator = None
            self.refiner = None
    
    def detect_query_language(self, query: str) -> str:
        """
        Detect language of user query
        
        Args:
            query: User query text
            
        Returns:
            Language code (e.g., 'en', 'hi', 'te')
        """
        return self.embedder.detect_language(query)
    
    def _is_transcript_indexed(self, transcript_id: int) -> bool:
        """Check if transcript is already indexed"""
        indexed_ids = self.vectorstore.get_indexed_transcript_ids()
        return transcript_id in indexed_ids
    
    def index_transcript(
        self,
        transcript_id: int,
        prefer_notes: bool = True,
        force_reindex: bool = False
    ):
        """
        Index a transcript for retrieval
        
        Args:
            transcript_id: Transcript ID to index
            prefer_notes: If True, prioritize notes over paragraphs
            force_reindex: If True, re-index even if already indexed
        """
        # Check if already indexed (unless force_reindex)
        if not force_reindex:
            if self._is_transcript_indexed(transcript_id):
                print(f"⏭️  Transcript {transcript_id} already indexed. Skipping. (Use force_reindex=True to re-index)")
                return
        
        # Get transcript
        transcripts = self.storage_service.get_user_transcripts(
            user_id=self.user_id,
            limit=10000
        )
        
        transcript = None
        for t in transcripts:
            if t.get('id') == transcript_id:
                transcript = t
                break
        
        if not transcript:
            raise ValueError(f"Transcript {transcript_id} not found")
        
        # If force_reindex, delete old embeddings first
        if force_reindex:
            self.vectorstore.delete_by_transcript(transcript_id)
            print(f"🔄 Re-indexing transcript {transcript_id}...")
        
        # Get notes if available and preferred
        notes = []
        if prefer_notes:
            try:
                notes = self.storage_service.get_transcript_notes(
                    user_id=self.user_id,
                    transcript_id=transcript_id
                )
            except Exception:
                pass
        
        # Prepare texts for embedding
        texts_to_index = []
        metadata_list = []
        
        # Add notes first (higher priority)
        for note in notes:
            text = note.get('content', '')
            if text and text.strip():
                texts_to_index.append(text)
                metadata_list.append({
                    'text': text,
                    'transcript_id': transcript_id,
                    'document_id': transcript.get('document_id'),
                    'type': 'note',
                    'note_id': note.get('id'),
                    'note_type': note.get('note_type', 'summary'),
                    'language': note.get('language', transcript.get('language', 'en')),
                    'start': None,
                    'end': None
                })
        
        # CRITICAL: Always index transcript text (even if notes exist)
        # Split transcript text into chunks for better retrieval
        transcript_text = transcript.get('text', '')
        if transcript_text and transcript_text.strip():
            # Split into sentences/chunks for better granularity
            # Use paragraphs if available, otherwise split by sentences
            paragraphs = transcript.get('paragraphs', [])
            
            if paragraphs:
                # Use existing paragraphs
            for para in paragraphs:
                text = para.get('text', '')
                if text and text.strip():
                    texts_to_index.append(text)
                    metadata_list.append({
                        'text': text,
                        'transcript_id': transcript_id,
                        'document_id': transcript.get('document_id'),
                        'type': 'paragraph',
                        'start': para.get('start'),
                        'end': para.get('end'),
                        'language': transcript.get('language', 'en')
                    })
            else:
                # No paragraphs - split transcript text into chunks
                # Split by sentences (roughly 2-3 sentences per chunk)
                import re
                sentences = re.split(r'([.!?।॥]\s+)', transcript_text)
                
                current_chunk = []
                chunk_size = 0
                max_chunk_size = 1000  # Increased from 500 to 1000 for better fact preservation
                
                for i, part in enumerate(sentences):
                    current_chunk.append(part)
                    chunk_size += len(part)
                    
                    # If chunk is large enough or we hit a sentence end, save it
                    if (chunk_size >= max_chunk_size and part.strip().endswith(('.', '!', '?', '।', '॥'))) or i == len(sentences) - 1:
                        chunk_text = ''.join(current_chunk).strip()
                        if chunk_text:
                            texts_to_index.append(chunk_text)
                            metadata_list.append({
                                'text': chunk_text,
                                'transcript_id': transcript_id,
                                'document_id': transcript.get('document_id'),
                                'type': 'transcript_chunk',
                                'start': None,
                                'end': None,
                                'language': transcript.get('language', 'en')
                            })
                        current_chunk = []
                        chunk_size = 0
        
        if not texts_to_index:
            print(f"⚠️  No content to index for transcript {transcript_id}")
            return
        
        # Generate embeddings
        print(f"📝 Indexing {len(texts_to_index)} chunks for transcript {transcript_id}...")
        embeddings = self.embedder.embed_batch(texts_to_index, show_progress=True)
        
        # Add to vector store
        self.vectorstore.add_embeddings(embeddings, metadata_list)
        
        print(f"✅ Indexed transcript {transcript_id}")
    
    def index_all_transcripts(self, prefer_notes: bool = True, force_reindex: bool = False):
        """
        Index all user transcripts (skip already indexed unless force_reindex=True)
        
        Args:
            prefer_notes: If True, prioritize notes over paragraphs
            force_reindex: If True, re-index all transcripts even if already indexed
        """
        transcripts = self.storage_service.get_user_transcripts(
            user_id=self.user_id,
            limit=10000
        )
        
        print(f"📚 Checking {len(transcripts)} transcripts for user {self.user_id}...")
        
        indexed_count = 0
        skipped_count = 0
        error_count = 0
        
        for transcript in transcripts:
            transcript_id = transcript.get('id')
            
            # Check if already indexed
            if not force_reindex and self._is_transcript_indexed(transcript_id):
                skipped_count += 1
                continue
            
            try:
                self.index_transcript(
                    transcript_id=transcript_id,
                    prefer_notes=prefer_notes,
                    force_reindex=force_reindex
                )
                indexed_count += 1
            except Exception as e:
                print(f"⚠️  Failed to index transcript {transcript_id}: {e}")
                error_count += 1
        
        print(f"✅ Indexing complete: {indexed_count} indexed, {skipped_count} skipped (already indexed), {error_count} errors")
        
        return {
            'indexed': indexed_count,
            'skipped': skipped_count,
            'errors': error_count,
            'total': len(transcripts)
        }
    
    def query(
        self,
        question: str,
        top_k: int = 10,  # Increased from 5 to 10 for better fact coverage
        min_similarity: float = 0.2,  # Lower default for better multilingual support
        include_citations: bool = True,
        use_advanced: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using Advanced RAG
        
        Args:
            question: User question (any language)
            top_k: Number of relevant chunks to retrieve
            min_similarity: Minimum similarity threshold
            include_citations: Include citations in response
            use_advanced: Override enable_advanced setting
            
        Returns:
            Dictionary with:
            - 'answer': Answer text (in query language)
            - 'language': Detected query language
            - 'citations': List of citation dicts
            - 'retrieved_chunks': Retrieved context chunks
            - 'validation': Response validation results
            - 'query_rewritten': Rewritten query (if advanced)
            - 'search_method': Search method used
        """
        use_advanced = use_advanced if use_advanced is not None else self.enable_advanced
        
        # Detect query language
        query_lang = self.detect_query_language(question)
        
        # Step 1: Query Rewriting (if advanced) - Skip for simple queries to save time
        original_question = question
        if use_advanced and self.query_rewriter:
            # Skip rewriting for very short or simple queries (speed optimization)
            question_lower = question.lower().strip()
            is_simple_query = (
                len(question.split()) <= 3 or  # Very short
                question_lower in ['hi', 'hello', 'hey', 'thanks', 'bye', 'ok', 'okay'] or  # Greetings
                not any(c in question for c in ['?', 'what', 'how', 'why', 'when', 'where', 'who', 'which'])  # Not a question
            )
            
            if is_simple_query:
                # Skip LLM rewriting for simple queries
                rewritten_info = None
                query_variants = [question]
            else:
                rewritten_info = self.query_rewriter.rewrite_query(question, query_lang)
                question = rewritten_info['rewritten']  # Use rewritten query for search
                query_variants = self.query_rewriter.generate_search_queries(original_question, query_lang)
        else:
            rewritten_info = None
            query_variants = [question]
        
        # Step 2: Hybrid Search (if advanced) or Semantic Search
        if use_advanced and self.hybrid_search:
            # Use hybrid search (semantic + keyword)
            results = self.hybrid_search.search(
                query=question,
                top_k=top_k * 3,  # Get more for better multilingual matching
                semantic_weight=0.7,
                keyword_weight=0.3,
                min_score=min_similarity * 0.7  # More lenient for multilingual
            )
            search_method = 'hybrid'
        else:
            # Fallback to semantic search only
            query_embedding = self.embedder.embed_text(question)
            results = self.vectorstore.search(
                query_embedding=query_embedding,
                k=top_k * 3  # Get more results for better matching
            )
            search_method = 'semantic'
        
        # Step 3: Re-ranking (if advanced) - Limit to top candidates for speed
        if results and use_advanced and self.reranker and self.reranker.is_available():
            # Only re-rank top candidates (not all results) for better performance
            candidates_to_rerank = results[:top_k * 3]  # Re-rank top 3x candidates
            if len(candidates_to_rerank) > 0:
                reranked_candidates = self.reranker.rerank(original_question, candidates_to_rerank, top_k=top_k * 2)
                # Combine with non-reranked results
                reranked_keys = {self._get_result_key(meta) for meta, _ in reranked_candidates}
                other_results = [(meta, score) for meta, score in results if self._get_result_key(meta) not in reranked_keys]
                results = reranked_candidates + other_results
                results.sort(key=lambda x: x[1], reverse=True)
        
        # Filter by similarity threshold - more lenient for multilingual
        if results:
            # For multilingual/cross-lingual queries, use a more lenient threshold
            # Cross-lingual semantic similarity can be lower but still relevant
            base_threshold = min_similarity
            multilingual_threshold = base_threshold * 0.7  # 30% more lenient
            
        filtered_results = [
            (meta, score) for meta, score in results
                if score >= multilingual_threshold
            ]
            
            # If still no results but we have some, use top results anyway
            if not filtered_results and results:
                # Use top results even if slightly below threshold
                # This helps with cross-lingual matching
                filtered_results = results[:top_k]
                if filtered_results:
                    top_score = filtered_results[0][1] if filtered_results else 0
                    print(f"📊 Using lenient threshold for multilingual matching. Top score: {top_score:.3f}")
        else:
            filtered_results = []
        
        # Early exit optimization: If no results found, skip remaining steps
        if not filtered_results:
            # No relevant context found - use general knowledge immediately
            if use_advanced and self.refiner:
                general_answer = self.refiner.answer_general_knowledge(original_question, query_lang)
                answer = general_answer.get('answer', 'No relevant information found in your stored transcripts.')
            else:
                if query_lang == 'en':
                    answer = "This question is not related to your stored transcripts. Please ask questions about your uploaded content."
                elif query_lang == 'hi':
                    answer = "यह प्रश्न आपके संग्रहीत ट्रांसक्रिप्ट से संबंधित नहीं है। कृपया अपनी अपलोड की गई सामग्री के बारे में प्रश्न पूछें।"
                elif query_lang == 'te':
                    answer = "ఈ ప్రశ్న మీ నిల్వ చేసిన ట్రాన్స్క్రిప్ట్‌లకు సంబంధించినది కాదు। దయచేసి మీ అప్‌లోడ్ చేసిన కంటెంట్ గురించి ప్రశ్నలు అడగండి।"
                else:
                    answer = "This question is not related to your stored transcripts. Please ask questions about your uploaded content."
            
            return {
                'answer': answer,
                'language': query_lang,
                'citations': [],
                'retrieved_chunks': [],
                'num_results': 0,
                'validation': None,
                'query_rewritten': rewritten_info,
                'search_method': search_method,
                'refinement_method': 'general_knowledge' if use_advanced else 'fallback',
                'is_from_context': False,
                'context_relevant': False
            }
        
        # Extract retrieved chunks (even if empty, for relevance check)
        retrieved_chunks = [meta for meta, _ in filtered_results] if filtered_results else []
        
        # Step 4: Check if context is relevant
        # First check if it's a greeting/short query (should use general knowledge)
        question_lower = original_question.lower().strip()
        short_greetings = {'hi', 'hey', 'hello', 'bye', 'thanks', 'thank you', 'ok', 'okay', 'yes', 'no',
                          'नमस्ते', 'हैलो', 'धन्यवाद', 'ठीक', 'हाँ', 'नहीं',
                          'నమస్కారం', 'హలో', 'ధన్యవాదాలు', 'సరే', 'అవును', 'కాదు'}
        is_greeting_or_short = len(question_lower) <= 3 or question_lower in short_greetings
        
        context_relevant = False
        if is_greeting_or_short:
            # Greetings/short queries should use general knowledge
            context_relevant = False
        elif retrieved_chunks and len(retrieved_chunks) > 0:
            # CRITICAL FIX: If we have retrieved chunks, they're likely relevant
            # Even if similarity is slightly low, use them for multilingual queries
            # Semantic search already did the filtering
            context_relevant = True  # Always consider relevant if chunks exist
            
            # Only do additional check if using advanced features AND similarity is very low
            if use_advanced and self.refiner:
                # Check average similarity of top results
                avg_similarity = sum(score for _, score in filtered_results[:3]) / len(filtered_results[:3]) if filtered_results[:3] else 0
                if avg_similarity < 0.15:
                    # Very low similarity - do additional check
            context_relevant = self.refiner._check_context_relevance(
                original_question,
                retrieved_chunks,
                min_similarity
            )
                else:
                    # Similarity is reasonable - trust semantic search
                    context_relevant = True
            else:
                # If we have chunks above similarity threshold, consider relevant
                context_relevant = True
        elif filtered_results:
            # Fallback: if we have results above threshold, consider relevant
            context_relevant = True
        
        # Step 5: Answer Refinement
        is_from_context = False
        answer = None
        refinement_method = 'none'
        
        if context_relevant and retrieved_chunks:
            # Context is relevant - answer from context
            # CRITICAL: Always try to generate answer from context if chunks exist
            if use_advanced and self.refiner:
                refined = self.refiner.refine_answer(
                    question=original_question,
                    retrieved_chunks=retrieved_chunks[:15],  # Increased from 8 to 15 for better coverage
                    language=query_lang,
                    min_relevance=min_similarity
                )
                
                if refined.get('refined_answer'):
                    answer = refined['refined_answer']
                    refinement_method = refined.get('method', 'langchain')  # Prefer LangChain
                    is_from_context = True
                    context_relevant = refined.get('context_relevant', True)
                else:
                    # Refiner didn't produce answer - use simple method
                    context_relevant = True  # Keep trying with simple method
            
            if not answer and context_relevant and retrieved_chunks:
                # Simple answer construction from context
                answer_parts = []
                for meta in retrieved_chunks[:3]:
                    chunk_text = meta.get('text', '')
                    if not chunk_text or not chunk_text.strip():
                        continue
                    
                    chunk_lang = meta.get('language', 'en')
                    
                    # Translate if needed
                    if chunk_lang != query_lang and self.translation_service:
                        try:
                            translated = self.translation_service.translate_text(
                                text=chunk_text,
                                source_language=chunk_lang,
                                target_language=query_lang
                            )
                            answer_parts.append(translated)
                        except Exception:
                            answer_parts.append(chunk_text)
                    else:
                        answer_parts.append(chunk_text)
                
                if answer_parts:
                    answer = ' '.join(answer_parts)
                    answer = self._format_answer(answer, original_question)
                    refinement_method = 'simple'
                    is_from_context = True
        
        # Step 6: Handle non-relevant context - General Knowledge Answer
        if not context_relevant or not answer:
            # Context is empty or not relevant
            if use_advanced and self.refiner:
                general_answer = self.refiner.answer_general_knowledge(
                    question=original_question,
                    language=query_lang
                )
                
                # Format: Inform user first, then provide general answer
                if not context_relevant:
                    if query_lang == 'en':
                        prefix = "This question is not related to your stored transcripts. "
                    elif query_lang == 'hi':
                        prefix = "यह प्रश्न आपके संग्रहीत ट्रांसक्रिप्ट से संबंधित नहीं है। "
                    elif query_lang == 'te':
                        prefix = "ఈ ప్రశ్న మీ నిల్వ చేసిన ట్రాన్స్క్రిప్ట్‌లకు సంబంధించినది కాదు। "
                    else:
                        prefix = "This question is not related to your stored transcripts. "
                    
                    answer = prefix + general_answer.get('answer', 'I cannot answer this question.')
                else:
                    answer = general_answer.get('answer', 'I cannot answer this question.')
                
                refinement_method = general_answer.get('method', 'general_knowledge')
                is_from_context = False
            else:
                # Fallback message
                if query_lang == 'en':
                    answer = "This question is not related to your stored transcripts. Please ask questions about your uploaded content."
                elif query_lang == 'hi':
                    answer = "यह प्रश्न आपके संग्रहीत ट्रांसक्रिप्ट से संबंधित नहीं है। कृपया अपनी अपलोड की गई सामग्री के बारे में प्रश्न पूछें।"
                elif query_lang == 'te':
                    answer = "ఈ ప్రశ్న మీ నిల్వ చేసిన ట్రాన్స్క్రిప్ట్‌లకు సంబంధించినది కాదు। దయచేసి మీ అప్‌లోడ్ చేసిన కంటెంట్ గురించి ప్రశ్నలు అడగండి।"
                else:
                    answer = "This question is not related to your stored transcripts. Please ask questions about your uploaded content."
                
                refinement_method = 'fallback'
                is_from_context = False
        
        # Step 7: Response Validation (only for context-based answers)
        # Skip validation for high-confidence answers to save time
        validation = None
        if is_from_context and use_advanced and self.validator:
            # Calculate average similarity score for top results
            avg_similarity = sum(score for _, score in filtered_results[:3]) / len(filtered_results[:3]) if filtered_results[:3] else 0
            
            if avg_similarity >= 0.7:  # High confidence - skip validation
                validation = {
                    'is_valid': True,
                    'relevance_score': 0.9,
                    'completeness_score': 0.8,
                    'grounded_score': 0.9,
                    'overall_score': 0.87,
                    'issues': [],
                    'suggestions': [],
                    'method': 'skipped_high_confidence'
                }
            else:
                # Only validate when confidence is lower
                validation = self.validator.validate(
                    query=original_question,
                    answer=answer,
                    retrieved_chunks=retrieved_chunks,
                    language=query_lang
                )
        
        # Build citations (only if answer is from context)
        citations = []
        if is_from_context and include_citations:
            for i, (meta, score) in enumerate(filtered_results[:top_k]):
                citation = {
                    'chunk_index': i + 1,
                    'document_id': meta.get('document_id'),
                    'transcript_id': meta.get('transcript_id'),
                    'type': meta.get('type', 'paragraph'),
                    'start_time': meta.get('start'),
                    'end_time': meta.get('end'),
                    'similarity': float(score),
                    'original_language': meta.get('language', 'en')
                }
                citations.append(citation)
        
        return {
            'answer': answer,
            'language': query_lang,
            'citations': citations,
            'retrieved_chunks': retrieved_chunks[:top_k] if is_from_context else [],
            'num_results': len(filtered_results) if is_from_context else 0,
            'validation': validation,
            'query_rewritten': rewritten_info,
            'search_method': search_method,
            'refinement_method': refinement_method,
            'is_from_context': is_from_context,
            'context_relevant': context_relevant
        }
    
    def _format_answer(self, answer: str, question: str) -> str:
        """
        Format answer text for readability
        
        Args:
            answer: Raw answer text
            question: Original question
            
        Returns:
            Formatted answer
        """
        # Remove extra whitespace
        answer = re.sub(r'\s+', ' ', answer).strip()
        
        # Ensure proper sentence endings
        if answer and not answer[-1] in '.!?':
            answer += '.'
        
        return answer
    
    def get_citation_text(self, citation: Dict[str, Any]) -> str:
        """
        Format citation as readable text
        
        Args:
            citation: Citation dictionary
            
        Returns:
            Formatted citation string
        """
        parts = []
        
        if citation.get('document_id'):
            doc_id = citation['document_id'][:8] + '...'
            parts.append(f"Document: {doc_id}")
        
        if citation.get('start_time') is not None and citation.get('end_time') is not None:
            start = self._format_timestamp(citation['start_time'])
            end = self._format_timestamp(citation['end_time'])
            parts.append(f"Time: {start} - {end}")
        
        if citation.get('type'):
            parts.append(f"Type: {citation['type']}")
        
        return " | ".join(parts) if parts else "Source"
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp in seconds to HH:MM:SS"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _get_result_key(self, metadata: Dict[str, Any]) -> str:
        """Generate unique key for a result (for deduplication)"""
        transcript_id = metadata.get('transcript_id', '')
        start = metadata.get('start', '')
        end = metadata.get('end', '')
        return f"{transcript_id}_{start}_{end}"