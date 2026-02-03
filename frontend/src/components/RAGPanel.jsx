import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './RAGPanel.css'

const API_URL = 'http://localhost:8000'

function RAGPanel({ user }) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [citations, setCitations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [indexing, setIndexing] = useState(false)
  const [stats, setStats] = useState(null)
  const [deletingEmbeddings, setDeletingEmbeddings] = useState(false)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/rag/stats`, {
        params: { user_id: user.user_id }
      })
      setStats(response.data)
    } catch (err) {
      // Stats not critical, fail silently
      console.log('Stats not available:', err)
    }
  }
  
  const getStatsDisplay = () => {
    if (!stats) return null
    const vectors = stats.num_vectors || 0
    const transcripts = stats.indexed_transcript_count || 0
    return `${vectors} vectors from ${transcripts} transcripts`
  }

  const handleIndexAll = async () => {
    // Ask user: OK = skip duplicates (default), Cancel = reindex all
    const skipDuplicates = window.confirm(
      'Index transcripts for question-answering?\n\n' +
      '✅ Click OK: Index only NEW transcripts (skip already indexed) - Recommended\n' +
      '🔄 Click Cancel: Re-index ALL transcripts (including already indexed)'
    )
    
    // skipDuplicates: true = OK (skip), false = Cancel (reindex all)
    // force_reindex: false = skip duplicates, true = reindex all
    const forceReindex = !skipDuplicates

    setIndexing(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('user_id', user.user_id)
      formData.append('prefer_notes', 'true')
      formData.append('force_reindex', forceReindex.toString())

      const response = await axios.post(`${API_URL}/api/rag/index-all`, formData)
      const result = response.data.indexing_result
      alert(
        `✅ Indexing complete!\n` +
        `- ${result.indexed} transcripts indexed\n` +
        `- ${result.skipped} transcripts skipped (already indexed)\n` +
        `- ${result.errors} errors`
      )
      loadStats()
    } catch (err) {
      setError(err.response?.data?.detail || 'Indexing failed')
    } finally {
      setIndexing(false)
    }
  }

  const handleDeleteAllEmbeddings = async () => {
    if (!window.confirm(
      '⚠️ WARNING: This will delete ALL embeddings for your account!\n\n' +
      'This means you will need to re-index all transcripts to use question-answering again.\n\n' +
      'Are you sure you want to continue?'
    )) {
      return
    }

    setDeletingEmbeddings(true)
    setError('')
    try {
      await axios.delete(`${API_URL}/api/rag/embeddings/all`, {
        params: { user_id: user.user_id }
      })
      alert('✅ All embeddings deleted successfully. Re-index transcripts to use question-answering again.')
      loadStats()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete embeddings')
    } finally {
      setDeletingEmbeddings(false)
    }
  }

  const handleQuery = async (e) => {
    e.preventDefault()
    if (!question.trim()) {
      setError('Please enter a question')
      return
    }

    setLoading(true)
    setError('')
    setAnswer(null)
    setCitations([])

    try {
      const formData = new FormData()
      formData.append('question', question)
      formData.append('user_id', user.user_id)
      formData.append('top_k', '5')
      formData.append('min_similarity', '0.3')
      formData.append('use_advanced', 'true')  // Enable advanced RAG features

      const response = await axios.post(`${API_URL}/api/rag/query`, formData)
      
      setAnswer(response.data)
      setCitations(response.data.citations || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  const formatTimestamp = (seconds) => {
    if (seconds === null || seconds === undefined) return 'N/A'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)
    return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="rag-panel">
      <div className="rag-header">
        <div>
          <h2>🤖 Ask Questions</h2>
          <div className="list-subtitle">Query your transcripts with AI-powered search</div>
        </div>
        <div className="rag-actions">
          <button
            onClick={handleIndexAll}
            disabled={indexing}
            className="index-btn"
          >
            {indexing ? 'Indexing...' : '📚 Index All Transcripts'}
          </button>
          {stats && stats.num_vectors > 0 && (
            <button
              onClick={handleDeleteAllEmbeddings}
              disabled={deletingEmbeddings}
              className="delete-embeddings-btn"
              title="Delete all embeddings"
            >
              {deletingEmbeddings ? 'Deleting...' : '🗑️ Delete All Embeddings'}
            </button>
          )}
          {stats && (
            <span className="stats-badge" title={getStatsDisplay()}>
              {getStatsDisplay() || `${stats.num_vectors || 0} vectors indexed`}
            </span>
          )}
        </div>
      </div>

      <div className="rag-info">
        <p>
          💡 Ask questions about your transcripts in any language. 
          Answers will be in the same language as your question.
        </p>
      </div>

      <form onSubmit={handleQuery} className="rag-form">
        <div className="form-group">
          <label>Your Question</label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a question about your transcripts... (e.g., 'What was discussed about AI?', 'क्या AI के बारे में चर्चा हुई?')"
            rows={3}
            disabled={loading}
            className="question-input"
          />
        </div>

        {error && <div className="error">{error}</div>}

        <button
          type="submit"
          disabled={loading || !question.trim()}
          className="submit-btn"
        >
          {loading ? 'Searching...' : '🔍 Ask Question'}
        </button>
      </form>

      {answer && (
        <div className="rag-result">
          <div className="answer-section">
            <h3>Answer</h3>
            <div className="answer-text">{answer.answer}</div>
            <div className="answer-meta">
              <span>Language: {answer.language?.toUpperCase() || 'Auto'}</span>
              {answer.is_from_context !== undefined && (
                <span className={answer.is_from_context ? 'source-badge context' : 'source-badge general'}>
                  {answer.is_from_context ? '📚 From Your Transcripts' : '🌐 General Knowledge'}
                </span>
              )}
              {answer.num_results > 0 && (
                <span>{answer.num_results} relevant chunks found</span>
              )}
              {answer.search_method && (
                <span className="method-badge">Search: {answer.search_method}</span>
              )}
              {answer.refinement_method && (
                <span className="method-badge">Refinement: {answer.refinement_method}</span>
              )}
            </div>
            
            {!answer.is_from_context && (
              <div className="general-knowledge-notice">
                <p>
                  <strong>Note:</strong> This answer is based on general knowledge, not your stored transcripts. 
                  To get answers from your uploaded content, please ask questions related to your transcripts.
                </p>
              </div>
            )}
            
            {answer.validation && (
              <div className="validation-section">
                <h4>Quality Validation</h4>
                <div className="validation-scores">
                  <div className="score-item">
                    <span className="score-label">Relevance:</span>
                    <span className="score-value">{(answer.validation.relevance_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="score-item">
                    <span className="score-label">Completeness:</span>
                    <span className="score-value">{(answer.validation.completeness_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="score-item">
                    <span className="score-label">Grounded:</span>
                    <span className="score-value">{(answer.validation.grounded_score * 100).toFixed(0)}%</span>
                  </div>
                  <div className="score-item overall">
                    <span className="score-label">Overall:</span>
                    <span className="score-value">{(answer.validation.overall_score * 100).toFixed(0)}%</span>
                  </div>
                </div>
                {answer.validation.issues && answer.validation.issues.length > 0 && (
                  <div className="validation-issues">
                    <strong>Issues:</strong>
                    <ul>
                      {answer.validation.issues.map((issue, idx) => (
                        <li key={idx}>{issue}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {answer.validation.suggestions && answer.validation.suggestions.length > 0 && (
                  <div className="validation-suggestions">
                    <strong>Suggestions:</strong>
                    <ul>
                      {answer.validation.suggestions.map((suggestion, idx) => (
                        <li key={idx}>{suggestion}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {citations.length > 0 && (
            <div className="citations-section">
              <h3>Sources & Citations</h3>
              <div className="citations-list">
                {citations.map((citation, idx) => (
                  <div key={idx} className="citation-card">
                    <div className="citation-header">
                      <span className="citation-number">#{idx + 1}</span>
                      <span className="citation-type">{citation.type}</span>
                      {citation.similarity && (
                        <span className="similarity-badge">
                          {(citation.similarity * 100).toFixed(1)}% match
                        </span>
                      )}
                    </div>
                    <div className="citation-details">
                      {citation.document_id && (
                        <div className="citation-detail">
                          <strong>Document:</strong> {citation.document_id.substring(0, 12)}...
                        </div>
                      )}
                      {citation.start_time !== null && citation.end_time !== null && (
                        <div className="citation-detail">
                          <strong>Time:</strong> {formatTimestamp(citation.start_time)} - {formatTimestamp(citation.end_time)}
                        </div>
                      )}
                      {citation.original_language && (
                        <div className="citation-detail">
                          <strong>Language:</strong> {citation.original_language.toUpperCase()}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {stats && stats.num_vectors === 0 && (
        <div className="empty-state">
          <p>⚠️ No transcripts indexed yet. Click "Index All Transcripts" to enable question-answering.</p>
        </div>
      )}
    </div>
  )
}

export default RAGPanel
