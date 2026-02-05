import React from 'react'
import './ConversationHistoryModal.css'

function ConversationHistoryModal({ conversation, isOpen, onClose }) {
  if (!isOpen) return null
  
  // If no conversation provided, show empty state
  if (!conversation) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content conversation-modal-content" onClick={(e) => e.stopPropagation()}>
          <div className="modal-header">
            <h3>💬 Conversation History</h3>
            <button className="modal-close" onClick={onClose}>×</button>
          </div>
          <div className="modal-body conversation-modal-body">
            <div className="empty-conversation">No conversation data available. Please try selecting a conversation first.</div>
          </div>
          <div className="modal-footer">
            <button onClick={onClose} className="modal-close-btn">Close</button>
          </div>
        </div>
      </div>
    )
  }

  // Get messages array (handle both array and undefined)
  const messages = conversation.messages || []
  
  // Group messages into Q&A pairs
  const qaPairs = []
  let currentQuestion = null
  
  messages.forEach((msg) => {
    if (msg.role === 'user') {
      // If there's a pending question, add it as unanswered
      if (currentQuestion) {
        qaPairs.push({ question: currentQuestion, answer: null })
      }
      currentQuestion = msg
    } else if (msg.role === 'assistant') {
      if (currentQuestion) {
        qaPairs.push({ question: currentQuestion, answer: msg })
        currentQuestion = null
      } else {
        // Orphaned answer (shouldn't happen, but handle it)
        qaPairs.push({ question: null, answer: msg })
      }
    }
  })
  
  // Add any remaining question
  if (currentQuestion) {
    qaPairs.push({ question: currentQuestion, answer: null })
  }

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content conversation-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>💬 {conversation.title || 'Conversation History'}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body conversation-modal-body">
          {qaPairs.length === 0 ? (
            <div className="empty-conversation">No messages in this conversation yet.</div>
          ) : (
            <div className="qa-pairs-list">
              {qaPairs.map((pair, idx) => (
                <div key={idx} className="qa-pair">
                  {pair.question && (
                    <div className="message-item question-item">
                      <div className="message-header">
                        <span className="message-icon">👤</span>
                        <span className="message-label">Question</span>
                        <span className="message-date">{formatDate(pair.question.created_at)}</span>
                      </div>
                      <div className="message-text question-text">{pair.question.content}</div>
                    </div>
                  )}
                  {pair.answer ? (
                    <div className="message-item answer-item">
                      <div className="message-header">
                        <span className="message-icon">🤖</span>
                        <span className="message-label">Answer</span>
                        <span className="message-date">{formatDate(pair.answer.created_at)}</span>
                      </div>
                      <div className="message-text answer-text">{pair.answer.content}</div>
                      {pair.answer.metadata && pair.answer.metadata.citations && pair.answer.metadata.citations.length > 0 && (
                        <div className="answer-metadata">
                          <span className="metadata-badge">
                            {pair.answer.metadata.citations.length} source{pair.answer.metadata.citations.length !== 1 ? 's' : ''}
                          </span>
                          {pair.answer.metadata.is_from_context && (
                            <span className="metadata-badge context-badge">From Your Transcripts</span>
                          )}
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="message-item answer-item pending">
                      <div className="message-text pending-text">No answer yet...</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="modal-footer">
          <span className="conversation-meta">
            {messages.length} message{messages.length !== 1 ? 's' : ''} • 
            Language: {conversation.language?.toUpperCase() || 'Auto'} • 
            Created: {formatDate(conversation.created_at)}
          </span>
        </div>
      </div>
    </div>
  )
}

export default ConversationHistoryModal
