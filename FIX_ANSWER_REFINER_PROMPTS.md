# Fix Answer Refiner Prompts - Manual Update Required

## Issue
The prompts in `src/rag/answer_refiner.py` are still the old version, causing answers to say "context doesn't provide specific details" even when context has all the information.

## Fix Required

Update `src/rag/answer_refiner.py` at lines 209-243:

### Replace lines 209-216 (Context Preparation):

```python
            # Prepare context from top chunks
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks[:5]):  # Use top 5 chunks
                text = chunk.get('text', '')
                if text:
                    context_parts.append(f"[Source {i+1}]: {text[:500]}")  # Increased limit for better context
            
            context = '\n\n'.join(context_parts)
```

**With:**

```python
            # Prepare context from top chunks - ensure we have valid text
            context_parts = []
            for i, chunk in enumerate(retrieved_chunks[:8]):  # Use top 8 chunks for more context
                text = chunk.get('text', '')
                if not text:
                    # Try alternative field names
                    text = chunk.get('content', '') or chunk.get('chunk_text', '')
                
                if text and text.strip():
                    # Use more context (up to 1200 chars) for better fact extraction
                    chunk_text = text[:1200] + "..." if len(text) > 1200 else text
                    context_parts.append(f"[Source {i+1}]: {chunk_text}")
            
            context = '\n\n'.join(context_parts) if context_parts else "No context available."
            
            # Debug: Log if context is empty
            if not context_parts:
                print(f"⚠️  WARNING: No valid text found in retrieved chunks!")
                print(f"   Chunks: {len(retrieved_chunks)}")
                print(f"   Sample chunk keys: {list(retrieved_chunks[0].keys()) if retrieved_chunks else 'No chunks'}")
                # Try simple fallback
                return self._refine_simple(question, retrieved_chunks, language)
```

### Replace lines 221-243 (Prompts):

```python
            system_prompt = f"""You are a helpful assistant that answers questions based on the user's stored transcripts.

CRITICAL RULES (apply to ALL languages):
1. Answer STRICTLY using only information from the provided context
2. Do NOT use any external knowledge or general information
3. If the context doesn't contain enough information, respond appropriately in {lang_name}
4. Ground your answer completely in the provided context
5. Be concise, clear, and accurate
6. Preserve ALL specific numbers, dates, names, and facts mentioned in the context
7. Do NOT simplify, omit, or change any factual information
8. Answer in {lang_name} language if the question is in {lang_name}, otherwise match the question language

For {lang_name} queries: Answer in {lang_name} language.
For other languages: Answer in the same language as the question."""
            
            user_prompt = f"""Question (in {lang_name}): {question}

Context from user's transcripts:
{context}

Provide a clear, well-structured answer based ONLY on the context above.
Answer in {lang_name} language.
Preserve all facts, numbers, dates, and names exactly as mentioned in the context."""
```

**With:**

```python
            system_prompt = f"""You are a factual information extractor. Your job is to extract ALL relevant facts, numbers, dates, and details from the context.

CRITICAL EXTRACTION RULES (apply to ALL languages):
1. Extract EVERY number mentioned (e.g., "25 करोड़", "11 years", "2015", "2026-2027")
2. Extract EVERY date mentioned (e.g., "26 November 2015", "2026-2027")
3. Extract EVERY specific fact (e.g., "Constitution Day", "Nation First", "poverty line")
4. DO NOT say "context doesn't provide" or "I cannot find" - if you see information, extract it
5. List ALL relevant points, not just a summary
6. Include exact numbers and dates in your answer
7. If context mentions multiple impacts, list ALL of them
8. Be comprehensive - don't omit details
9. Answer in {lang_name} language if the question is in {lang_name}, otherwise match the question language

FORMAT YOUR ANSWER:
- Start with a direct answer to the question
- List specific facts with numbers/dates
- Include all relevant details from context
- End with a summary if needed

IMPORTANT: The context contains detailed information. Extract ALL of it, not just a summary. Never say the context lacks information - use what is provided."""

            user_prompt = f"""Question: {question}

Context from user's transcripts (EXTRACT ALL FACTS FROM THIS):
{context}

Based ONLY on the context above, provide a comprehensive answer that:
1. Directly answers the question
2. Includes ALL numbers, dates, and specific facts mentioned
3. Lists all relevant points and impacts
4. Does NOT say "context doesn't provide" - use the facts from context
5. Be thorough and include all details

Answer in {lang_name} language."""
```

## After Update

The system will:
- Extract ALL numbers (25 करोड़, 11 years, etc.)
- Extract ALL dates (26 November 2015, 2026-2027)
- Extract ALL facts (Constitution Day, Nation First, etc.)
- NOT say "context doesn't provide"
- Give comprehensive answers with all details
