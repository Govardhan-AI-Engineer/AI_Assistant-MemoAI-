import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './ConversationsPanel.css'

const API_URL = 'http://localhost:8000'

function ConversationsPanel({ user, onSelectConversation, selectedConversationId }) {
  const [conversations, setConversations] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState(null)

  useEffect(() => {
    loadConversations()
  }, [])

  const loadConversations = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await axios.get(`${API_URL}/api/conversations`, {
        params: { user_id: user.user_id }
      })
      // API returns {conversations: [...], count: ...}
      setConversations(response.data?.conversations || response.data || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load conversations')
      console.error('Load conversations error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (conversationId, e) => {
    e.stopPropagation() // Prevent selecting conversation when clicking delete
    
    if (!window.confirm('Are you sure you want to delete this conversation?')) {
      return
    }

    setDeletingId(conversationId)
    try {
      await axios.delete(`${API_URL}/api/conversations/${conversationId}`, {
        params: { user_id: user.user_id }
      })
      // Remove from list
      setConversations(conversations.filter(conv => (conv.conversation_id || conv.id) !== conversationId))
      // If this was the selected conversation, clear selection
      if (selectedConversationId === conversationId) {
        onSelectConversation(null)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete conversation')
    } finally {
      setDeletingId(null)
    }
  }

  const formatDate = (dateString) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  if (loading) {
    return (
      <div className="conversations-panel">
        <div className="loading-state">Loading conversations...</div>
      </div>
    )
  }

  return (
    <div className="conversations-panel">
      <div className="conversations-header">
        <div>
          <h2>💬 Conversation History</h2>
          <div className="list-subtitle">View and manage your previous conversations</div>
        </div>
        <button
          onClick={loadConversations}
          className="refresh-btn"
          title="Refresh conversations"
        >
          🔄 Refresh
        </button>
      </div>

      {error && <div className="error">{error}</div>}

      {conversations.length === 0 ? (
        <div className="empty-state">
          <p>No conversations yet. Start asking questions to create your first conversation!</p>
        </div>
      ) : (
        <div className="conversations-list">
          {conversations.map((conversation) => (
            <div
              key={conversation.id}
              className={`conversation-item ${selectedConversationId === (conversation.conversation_id || conversation.id) ? 'selected' : ''}`}
              onClick={() => onSelectConversation(conversation)}
            >
              <div className="conversation-content">
                <div className="conversation-title">{conversation.title || 'Untitled Conversation'}</div>
                <div className="conversation-meta">
                  <span className="conversation-date">{formatDate(conversation.created_at || conversation.updated_at)}</span>
                  {conversation.language && (
                    <span className="conversation-lang">{conversation.language.toUpperCase()}</span>
                  )}
                  {conversation.message_count > 0 && (
                    <span className="conversation-count">{conversation.message_count} messages</span>
                  )}
                </div>
              </div>
              <button
                className="delete-conversation-btn"
                onClick={(e) => handleDelete(conversation.conversation_id || conversation.id, e)}
                disabled={deletingId === (conversation.conversation_id || conversation.id)}
                title="Delete conversation"
              >
                {deletingId === (conversation.conversation_id || conversation.id) ? '⏳' : '🗑️'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ConversationsPanel
