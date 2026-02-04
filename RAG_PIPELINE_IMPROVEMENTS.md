# RAG Pipeline Improvements - Comprehensive Fix

## Problem Analysis

The user uploads videos/audios in different languages, gets transcripts/notes/summaries, and asks queries in different languages. The RAG system was not extracting ALL changes comprehensively.

### Issues Identified:

1. **Chunk size too small (500 chars)**: Facts split across chunks
2. **Only 8 chunks used**: Missing relevant chunks with specific facts
3. **Context window too small (1200 chars)**: Truncating important information
4. **Question interpretation**: Not explicitly extracting ALL changes
5. **Retrieval gaps**: Split facts not all retrieved

## Fixes Applied

### 1. Increased Chunk Size During Indexing
- **File**: `src/rag/qa.py` line 202
- **Change**: `max_chunk_size = 500` → `max_chunk_size = 1000`
- **Impact**: Facts like "25 crore" and "11 years" stay together in same chunk

### 2. Increased Chunks Used for Answer Generation
- **File**: `src/rag/qa.py` line 479
- **Change**: `retrieved_chunks[:8]` → `retrieved_chunks[:15]`
- **Impact**: More comprehensive context, less chance of missing facts

### 3. Increased Context Window Per Chunk
- **Files**: 
  - `src/rag/answer_refiner.py` line 202
  - `src/rag/answer_refiner.py` line 229
  - `src/rag/langchain_qa.py` line 282
- **Change**: `text[:1200]` → `text[:2000]`
- **Impact**: More complete information per chunk, no truncation

### 4. Enhanced Prompt for "Changes" Questions
- **Files**: 
  - `src/rag/answer_refiner.py` line 289
  - `src/rag/langchain_qa.py` line 203
- **Added**: Explicit instruction to list ALL changes, impacts, developments
- **Impact**: LLM explicitly extracts every change mentioned

### 5. Updated Chunk Counts Throughout
- **Files**: Multiple locations
- **Change**: All `[:8]` → `[:15]` for better coverage
- **Impact**: Consistent use of 15 chunks across pipeline

## Complete Changes Summary

| Component | Before | After | Impact |
|-----------|--------|-------|--------|
| Chunk Size (Indexing) | 500 chars | 1000 chars | Facts stay together |
| Chunks Used (Answer) | 8 chunks | 15 chunks | More comprehensive |
| Context Window | 1200 chars | 2000 chars | No truncation |
| Prompt Emphasis | Generic | Explicit "ALL changes" | Better extraction |

## Expected Results

### Before:
- "India's development is described as rapidly progressing, making it the third-largest economic system in the world. They have a tangible effect at the grassroots level. The current prime minister is noted for always being stable."
- Missing: "25 crore", "11 years", "26 November 2015", "Constitution Day", etc.

### After:
- "India's development is described as rapidly progressing, making it the third-largest economic system in the world. Over eleven years, more than 25 crore people came above the poverty line. The policies and programs have had a significant impact at the grassroots level, not just limited to paper. In 2015, the Prime Minister declared 26 November as Constitution Day, emphasizing fundamental rights and duties. The budget for 2026-2027 focuses on reform, growth, and fiscal discipline."
- Includes: All specific numbers, dates, and changes mentioned

## Pipeline Flow (Updated)

1. **Indexing**:
   - Notes indexed first (if available)
   - Transcript text split into 1000-char chunks (was 500)
   - All chunks embedded with multilingual model

2. **Retrieval**:
   - Hybrid search retrieves top 30 candidates
   - Re-ranking narrows to top candidates
   - Top 15 chunks selected (was 8)

3. **Answer Generation**:
   - 15 chunks with 2000 chars each (was 8 chunks with 1200 chars)
   - Explicit prompt to extract ALL changes
   - Comprehensive extraction of all facts

## Testing

Test with: "What changes are described in the paragraph about India's development?"

Expected: All changes, numbers, dates, and facts comprehensively listed.
