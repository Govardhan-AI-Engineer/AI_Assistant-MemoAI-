# RAG System Testing Guide

## Issues Fixed

### ❌ Before
1. **Question 1 (Hindi)**: System asked for more context instead of answering
2. **Question 2 (English)**: System said "I don't have a transcript to refer to"
3. **Not indexing transcript text**: Only indexed notes/paragraphs
4. **Context relevance failing**: Keyword matching didn't work for multilingual

### ✅ After
1. **Always indexes transcript text**: Full transcript is now indexed
2. **Improved multilingual support**: Better context relevance for Hindi/Telugu
3. **LangChain integration**: Better prompt management and answer generation
4. **Enhanced prompts**: Multilingual prompts with explicit rules

## Installation

```bash
# Install LangChain (if not already installed)
pip install langchain>=0.1.0 langchain-core>=0.1.0
```

## Re-indexing Required

**IMPORTANT**: You need to re-index your transcripts to include the full transcript text.

### Option 1: Re-index via API
```bash
# Re-index a specific transcript
curl -X POST "http://localhost:8000/api/rag/index" \
  -F "transcript_id=1" \
  -F "user_id=1" \
  -F "prefer_notes=false" \
  -F "force_reindex=true"
```

### Option 2: Re-index All Transcripts
```bash
# Re-index all transcripts
curl -X POST "http://localhost:8000/api/rag/index-all" \
  -F "user_id=1" \
  -F "prefer_notes=false" \
  -F "force_reindex=true"
```

### Option 3: Via Frontend
1. Go to RAG Panel
2. Click "Index All Transcripts"
3. Check "Force Re-index"

## Test Questions

### Test 1: Simple Factual (Hindi)
**Question**: "ग्यारह वर्षों में कितने लोग गरीबी रेखा से ऊपर आए?"

**Expected Answer**: Should mention "25 करोड़" or "25 करोड़ से अधिक"

**What to Check**:
- ✅ Answers directly (no "need more context")
- ✅ Mentions "25 करोड़"
- ✅ Answer is in Hindi
- ✅ Cites source from transcript

### Test 2: Specific Date (English)
**Question**: "When did the Prime Minister declare Constitution Day and what was the date?"

**Expected Answer**: Should mention "2015" and "26 November" or "26 नवंबर"

**What to Check**:
- ✅ Mentions year 2015
- ✅ Mentions date 26 November
- ✅ Answer is complete
- ✅ Cites source

### Test 3: Conceptual (English)
**Question**: "What is the main message about fundamental rights and duties mentioned in the transcript?"

**Expected Answer**: Should explain that people talk about fundamental rights but don't discuss fundamental duties

**What to Check**:
- ✅ Explains rights vs duties concept
- ✅ Mentions the contrast
- ✅ Answer is coherent
- ✅ Based on transcript content

### Test 4: Economic Context (Hindi)
**Question**: "भारत की अर्थव्यवस्था की स्थिति क्या है?"

**Expected Answer**: Should mention "तीसरी बड़ी अर्थव्यवस्था"

**What to Check**:
- ✅ Mentions third largest economy
- ✅ Answer in Hindi
- ✅ Accurate information

## What Changed

### 1. Indexing (`src/rag/qa.py`)
- **Before**: Only indexed notes or paragraphs (if no notes)
- **After**: Always indexes transcript text, splits into chunks if needed

### 2. Context Relevance (`src/rag/answer_refiner.py`)
- **Before**: Keyword matching failed for multilingual
- **After**: Trusts semantic search results, better multilingual support

### 3. Answer Generation (`src/rag/answer_refiner.py`)
- **Before**: Simple prompts, weak answers
- **After**: LangChain integration, improved multilingual prompts

### 4. Query Logic (`src/rag/qa.py`)
- **Before**: Didn't always use retrieved context
- **After**: Always tries to use context when chunks exist

## Debugging

### Check if Transcript is Indexed
```python
from src.rag import RAGQAEngine
from src.memory import StorageService

storage = StorageService()
qa = RAGQAEngine(user_id=1, storage_service=storage)

# Check if indexed
is_indexed = qa._is_transcript_indexed(transcript_id=1)
print(f"Indexed: {is_indexed}")
```

### Check Retrieved Chunks
Look at the API response:
```json
{
  "answer": "...",
  "retrieved_chunks": [...],
  "num_results": 3,
  "is_from_context": true,
  "context_relevant": true
}
```

If `num_results` is 0, the transcript isn't indexed properly.

### Check Server Logs
Look for:
- `✅ Indexed transcript {id}` - Indexing successful
- `📝 Indexing {n} chunks` - Number of chunks indexed
- `✓ Using LangChain` - LangChain is working
- `⚠️  No content to index` - No content found (problem!)

## Expected Behavior

### ✅ Good Response
```json
{
  "answer": "ग्यारह वर्षों में 25 करोड़ से अधिक लोग गरीबी रेखा से ऊपर आ गए हैं।",
  "language": "hi",
  "num_results": 3,
  "is_from_context": true,
  "context_relevant": true,
  "citations": [...]
}
```

### ❌ Bad Response (Before Fix)
```json
{
  "answer": "मुझे कुछ जानकारी की आवश्यकता होगी...",
  "num_results": 0,
  "is_from_context": false
}
```

## Troubleshooting

### Problem: Still getting "no transcript" errors
**Solution**: 
1. Re-index transcripts with `force_reindex=true`
2. Check if transcript has text content
3. Verify indexing completed successfully

### Problem: Answers not in correct language
**Solution**:
1. Check `language` field in response
2. Verify translation service is working
3. Check if chunks are in correct language

### Problem: Incomplete answers
**Solution**:
1. Check if LangChain is installed
2. Verify GROQ_API_KEY is set
3. Check server logs for errors

## Next Steps

1. **Re-index all transcripts** (critical!)
2. **Test with provided questions**
3. **Verify answers are accurate**
4. **Check citations are correct**

## Summary

✅ **Fixed**: Transcript text now always indexed
✅ **Fixed**: Context relevance for multilingual
✅ **Added**: LangChain integration
✅ **Improved**: Answer generation with better prompts
✅ **Enhanced**: Query processing logic

The RAG system should now properly answer questions from your transcripts!
