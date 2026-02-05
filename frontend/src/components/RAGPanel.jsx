import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './RAGPanel.css'
import ConversationHistoryModal from './ConversationHistoryModal'

const API_URL = 'http://localhost:8000'

function RAGPanel({ user, selectedConversation, onConversationChange }) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [citations, setCitations] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [indexing, setIndexing] = useState(false)
  const [stats, setStats] = useState(null)
  const [deletingEmbeddings, setDeletingEmbeddings] = useState(false)
  const [conversationMessages, setConversationMessages] = useState([])
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [fullConversation, setFullConversation] = useState(null)

  useEffect(() => {
    loadStats()
  }, [])

  useEffect(() => {
    // Load conversation messages when conversation is selected
    if (selectedConversation) {
      loadConversationMessages()
    } else {
      setConversationMessages([])
    }
  }, [selectedConversation])

  const loadConversationMessages = async () => {
    if (!selectedConversation) {
      setConversationMessages([])
      setFullConversation(null)
      return
    }
    
    try {
      const conversationId = selectedConversation.conversation_id || selectedConversation.id
      console.log('Loading conversation messages for ID:', conversationId)
      const response = await axios.get(`${API_URL}/api/conversations/${conversationId}`, {
        params: { user_id: user.user_id }
      })
      // The API returns conversation with messages
      if (response.data) {
        // Ensure we're getting all messages (both user and assistant)
        const allMessages = (response.data.messages || []).filter(msg => msg && msg.role && msg.content)
        console.log('Loaded conversation:', {
          conversationId: response.data.conversation_id,
          messageCount: allMessages.length,
          messages: allMessages,
          fullData: response.data
        })
        setConversationMessages(allMessages)
        // Always store full conversation for modal (even if no messages yet)
        setFullConversation(response.data)
      } else {
        console.warn('No data in conversation response:', response.data)
        setConversationMessages([])
        // Still set fullConversation with basic info if available
        setFullConversation(selectedConversation)
      }
    } catch (err) {
      console.error('Failed to load conversation messages:', err)
      setConversationMessages([])
      // Keep basic conversation info even if loading fails
      setFullConversation(selectedConversation)
    }
  }

  const handleViewFullHistory = async () => {
    console.log('View Full History clicked', { 
      fullConversation, 
      conversationMessages: conversationMessages.length,
      selectedConversation 
    })
    
    // If we have fullConversation, show it immediately
    if (fullConversation) {
      setShowHistoryModal(true)
      return
    }
    
    // If we don't have fullConversation but have selectedConversation, try to load it
    if (selectedConversation) {
      console.log('Loading conversation for modal...')
      try {
        await loadConversationMessages()
        // Wait a bit for state to update
        setTimeout(() => {
          // Open modal - it will handle loading state or use selectedConversation directly
          setShowHistoryModal(true)
        }, 300)
      } catch (err) {
        console.error('Failed to load conversation for modal:', err)
        // Still try to show modal - it will handle empty state
        setShowHistoryModal(true)
      }
    } else {
      console.warn('No conversation selected')
      alert('No conversation selected. Please select a conversation from History tab first.')
    }
  }

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
      // Ensure user_id is sent as integer in query params
      const response = await axios.delete(`${API_URL}/api/rag/embeddings/all`, {
        params: { 
          user_id: parseInt(user.user_id, 10) 
        }
      })
      alert('✅ All embeddings deleted successfully. Re-index transcripts to use question-answering again.')
      loadStats()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete embeddings')
      console.error('Delete embeddings error:', err)
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
    setAnswer('')  // Start with empty string for streaming
    setCitations([])

    try {
      const formData = new FormData()
      formData.append('question', question)
      formData.append('user_id', user.user_id)
      formData.append('top_k', '10')
      formData.append('min_similarity', '0.3')
      formData.append('use_advanced', 'true')  // Enable advanced RAG features

      // Add conversation context if available, or generate new session_id for new conversation
      let currentConversationId = null
      let currentSessionId = null
      
      if (selectedConversation) {
        const conversationId = selectedConversation.conversation_id || selectedConversation.id
        const sessionId = selectedConversation.session_id
        if (conversationId) {
          formData.append('conversation_id', conversationId.toString())
          currentConversationId = conversationId
        }
        if (sessionId) {
          formData.append('session_id', sessionId)
          currentSessionId = sessionId
        }
      } else {
        // Generate a new session_id for a new conversation
        const newSessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
        formData.append('session_id', newSessionId)
        currentSessionId = newSessionId
      }

      // Use streaming endpoint
      const response = await fetch(`${API_URL}/api/rag/query/stream`, {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const errorText = await response.text()
        let errorData
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { detail: 'Streaming request failed' }
        }
        throw new Error(errorData.detail || 'Streaming request failed')
      }

      // Handle Server-Sent Events (SSE) stream
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullAnswer = ''
      let receivedCitations = []
      let receivedConversationId = currentConversationId
      let receivedSessionId = currentSessionId

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6)) // Remove 'data: ' prefix
              
              if (data.type === 'answer_chunk') {
                // Append chunk to answer
                fullAnswer += data.content || ''
                setAnswer(fullAnswer)
              } else if (data.type === 'citations') {
                receivedCitations = data.citations || []
                setCitations(receivedCitations)
              } else if (data.type === 'done') {
                receivedConversationId = data.conversation_id || receivedConversationId
                receivedSessionId = data.session_id || receivedSessionId
              } else if (data.type === 'error') {
                throw new Error(data.message || 'Streaming error')
              }
            } catch (err) {
              console.error('Error parsing SSE data:', err, 'Line:', line)
            }
          }
        }
      }
      
      // Update conversation if a new one was created
      if (receivedConversationId && !selectedConversation) {
        // Fetch the new conversation
        try {
          const convResponse = await axios.get(`${API_URL}/api/conversations/${receivedConversationId}`, {
            params: { user_id: user.user_id }
          })
          if (convResponse.data && onConversationChange) {
            onConversationChange(convResponse.data)
          }
        } catch (err) {
          console.error('Failed to load new conversation:', err)
        }
      } else if (receivedSessionId && !selectedConversation) {
        // If session_id was returned but no conversation_id yet, try to get conversation by session_id
        try {
          const convResponse = await axios.get(`${API_URL}/api/conversations/session/${receivedSessionId}`, {
            params: { user_id: user.user_id }
          })
          if (convResponse.data && onConversationChange) {
            onConversationChange(convResponse.data)
          }
        } catch (err) {
          // Conversation might not exist yet, that's okay
          console.log('Conversation not found by session_id yet:', err)
        }
      }
      
      // Reload conversation messages to show the new Q&A
      // Wait a bit for backend to save the messages
      setTimeout(async () => {
        if (receivedConversationId) {
          // If we got a conversation_id, make sure we have the conversation selected
          const currentConvId = selectedConversation?.conversation_id || selectedConversation?.id
          if (!selectedConversation || currentConvId !== receivedConversationId) {
            // Fetch and select the conversation
            try {
              console.log('Loading new conversation after query:', receivedConversationId)
              const convResponse = await axios.get(`${API_URL}/api/conversations/${receivedConversationId}`, {
                params: { user_id: user.user_id }
              })
              if (convResponse.data && onConversationChange) {
                console.log('Setting new conversation:', convResponse.data)
                onConversationChange(convResponse.data)
                // Messages will be loaded by useEffect when selectedConversation changes
              }
            } catch (err) {
              console.error('Failed to load conversation after query:', err)
            }
          } else {
            // Conversation already selected, just reload messages
            console.log('Reloading messages for existing conversation')
            await loadConversationMessages()
          }
        } else if (receivedSessionId && !selectedConversation) {
          // Try to get conversation by session_id
          try {
            const convResponse = await axios.get(`${API_URL}/api/conversations/session/${receivedSessionId}`, {
              params: { user_id: user.user_id }
            })
            if (convResponse.data && onConversationChange) {
              console.log('Setting conversation from session_id:', convResponse.data)
              onConversationChange(convResponse.data)
            }
          } catch (err) {
            console.log('Conversation not found by session_id yet, will retry:', err)
            // Retry after a longer delay
            setTimeout(async () => {
              try {
                const convResponse = await axios.get(`${API_URL}/api/conversations/session/${receivedSessionId}`, {
                  params: { user_id: user.user_id }
                })
                if (convResponse.data && onConversationChange) {
                  onConversationChange(convResponse.data)
                }
              } catch (retryErr) {
                console.error('Retry failed to load conversation:', retryErr)
              }
            }, 1000)
          }
        } else if (selectedConversation) {
          // Existing conversation, reload messages
          console.log('Reloading messages for selected conversation')
          await loadConversationMessages()
        }
      }, 500) // Wait 500ms for backend to save messages
      
      // Clear question after successful query
      setQuestion('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  const handleNewConversation = () => {
    // Remove the invalid setSelectedConversation call - it's a prop, not state
    setConversationMessages([])
    setQuestion('')
    setAnswer(null)
    setCitations([])
    if (onConversationChange) {
      onConversationChange(null)
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

      {selectedConversation && (
        <div className="conversation-context">
          <div className="conversation-context-header">
            <span className="conversation-title-badge">
              💬 {selectedConversation.title || 'Current Conversation'}
            </span>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              {/* Always show View Full History button when a conversation is selected */}
              <button
                onClick={handleViewFullHistory}
                className="view-history-btn"
                title="View full conversation history"
              >
                📜 View Full History
              </button>
              <button
                onClick={handleNewConversation}
                className="new-conversation-btn"
                title="Start new conversation"
              >
                ➕ New Conversation
              </button>
            </div>
          </div>
          {conversationMessages.length > 0 ? (
            <div className="conversation-preview">
              <div className="conversation-preview-header">
                <div className="conversation-preview-title">
                  Recent Q&A ({conversationMessages.length} messages)
                </div>
              </div>
              <div className="conversation-messages-preview">
                {(() => {
                  // Group messages into Q&A pairs for better display
                  // Get last 6 messages (3 Q&A pairs) - ensure we have valid messages
                  const validMessages = conversationMessages.filter(msg => msg && msg.role && msg.content)
                  const recentMessages = validMessages.slice(-6)
                  
                  console.log('Displaying messages:', {
                    total: conversationMessages.length,
                    valid: validMessages.length,
                    recent: recentMessages.length,
                    recentMessages
                  })
                  
                  const qaPairs = []
                  let currentQ = null
                  
                  recentMessages.forEach((msg) => {
                    if (msg.role === 'user') {
                      // If we have a pending Q, add it without answer
                      if (currentQ) {
                        qaPairs.push({ q: currentQ, a: null })
                      }
                      currentQ = msg
                    } else if (msg.role === 'assistant') {
                      if (currentQ) {
                        // Pair this answer with the current question
                        qaPairs.push({ q: currentQ, a: msg })
                        currentQ = null
                      } else {
                        // Orphaned answer (shouldn't happen, but handle it)
                        qaPairs.push({ q: null, a: msg })
                      }
                    }
                  })
                  
                  // Add any remaining question without answer
                  if (currentQ) {
                    qaPairs.push({ q: currentQ, a: null })
                  }
                  
                  // Get last 3 Q&A pairs
                  const displayPairs = qaPairs.slice(-3)
                  
                  if (displayPairs.length === 0) {
                    return (
                      <div style={{ color: '#666', fontStyle: 'italic', padding: '0.5rem' }}>
                        No messages to display
                      </div>
                    )
                  }
                  
                  return displayPairs.map((pair, idx) => (
                    <div key={pair.q?.id || pair.a?.id || idx} className="qa-preview-pair">
                      {pair.q && (
                        <div className="message-preview user">
                          <span className="message-role">👤</span>
                          <div className="message-content-wrapper">
                            <span className="message-label">Q:</span>
                            <span className="message-content">
                              {pair.q.content ? (pair.q.content.length > 80 ? pair.q.content.substring(0, 80) + '...' : pair.q.content) : '(empty question)'}
                            </span>
                          </div>
                        </div>
                      )}
                      {pair.a ? (
                        <div className="message-preview assistant">
                          <span className="message-role">🤖</span>
                          <div className="message-content-wrapper">
                            <span className="message-label">A:</span>
                            <span className="message-content">
                              {pair.a.content ? (pair.a.content.length > 80 ? pair.a.content.substring(0, 80) + '...' : pair.a.content) : '(empty answer)'}
                            </span>
                          </div>
                        </div>
                      ) : pair.q ? (
                        <div className="message-preview assistant pending">
                          <span className="message-role">⏳</span>
                          <span className="message-content">Waiting for answer...</span>
                        </div>
                      ) : null}
                    </div>
                  ))
                })()}
              </div>
            </div>
          ) : (
            <div className="conversation-preview">
              <div className="conversation-preview-title" style={{ color: '#666', fontStyle: 'italic' }}>
                No messages yet. Ask a question to start the conversation!
              </div>
            </div>
          )}
        </div>
      )}

      <div className="rag-info">
        <p>
          💡 Ask questions about your transcripts in any language. 
          Answers will be in the same language as your question.
          {selectedConversation && ' This conversation will remember previous questions and answers.'}
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

      {answer !== null && answer !== undefined && (
        <div className="rag-result">
          <div className="answer-section">
            <h3>Answer</h3>
            {/* Handle both streaming (string) and non-streaming (object) formats */}
            <div className="answer-text">
              {typeof answer === 'string' ? answer : (answer.answer || answer.text || '')}
            </div>
            {typeof answer === 'object' && (
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
            )}
            
            {typeof answer === 'object' && !answer.is_from_context && (
              <div className="general-knowledge-notice">
                <p>
                  <strong>Note:</strong> This answer is based on general knowledge, not your stored transcripts. 
                  To get answers from your uploaded content, please ask questions related to your transcripts.
                </p>
              </div>
            )}
            
            {typeof answer === 'object' && answer.validation && (
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

      <ConversationHistoryModal
        conversation={fullConversation}
        isOpen={showHistoryModal}
        onClose={() => setShowHistoryModal(false)}
      />
    </div>
  )
}

export default RAGPanel
