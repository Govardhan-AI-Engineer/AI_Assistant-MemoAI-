import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './TagsPanel.css'

const API_URL = 'http://localhost:8000'

function TagsPanel({ user, transcriptId, onTagsUpdate }) {
  const [tags, setTags] = useState([])
  const [transcriptTags, setTranscriptTags] = useState([])
  const [newTagName, setNewTagName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    loadTags()
    if (transcriptId) {
      loadTranscriptTags()
    }
  }, [transcriptId])

  const loadTags = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/api/tags`, {
        params: { user_id: user.user_id }
      })
      setTags(response.data.tags || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load tags')
    } finally {
      setLoading(false)
    }
  }

  const loadTranscriptTags = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/transcripts/${transcriptId}/tags`, {
        params: { user_id: user.user_id }
      })
      // This would need backend to return actual transcript tags
      // For now, we'll manage it in frontend
      setTranscriptTags(response.data.transcript_tags || [])
    } catch (err) {
      console.error('Failed to load transcript tags:', err)
      setTranscriptTags([])
    }
  }

  const createTag = async (e) => {
    e.preventDefault()
    if (!newTagName.trim()) return

    try {
      const formData = new FormData()
      formData.append('user_id', user.user_id)
      formData.append('name', newTagName.trim())

      await axios.post(`${API_URL}/api/tags`, formData)
      setNewTagName('')
      await loadTags()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create tag')
    }
  }

  const addTagToTranscript = async (tagId) => {
    if (!transcriptId) return

    try {
      const formData = new FormData()
      formData.append('user_id', user.user_id)
      formData.append('transcript_id', transcriptId)
      formData.append('tag_id', tagId)

      await axios.post(`${API_URL}/api/tags/transcript`, formData)
      await loadTranscriptTags()
      if (onTagsUpdate) onTagsUpdate()
      setError('') // Clear any previous errors
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to add tag')
    }
  }

  const removeTagFromTranscript = async (tagId) => {
    if (!transcriptId) return

    try {
      await axios.delete(`${API_URL}/api/transcripts/${transcriptId}/tags/${tagId}`, {
        params: { user_id: user.user_id }
      })
      await loadTranscriptTags()
      if (onTagsUpdate) onTagsUpdate()
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to remove tag')
    }
  }

  const deleteTag = async (tagId) => {
    if (!window.confirm('Are you sure you want to delete this tag? It will be removed from all transcripts and notes.')) {
      return
    }

    try {
      await axios.delete(`${API_URL}/api/tags/${tagId}`, {
        params: { user_id: user.user_id }
      })
      await loadTags()
      await loadTranscriptTags()
      if (onTagsUpdate) onTagsUpdate()
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete tag')
    }
  }

  if (!transcriptId) {
    return (
      <div className="tags-panel">
        <p>Select a transcript to manage tags.</p>
      </div>
    )
  }

  return (
    <div className="tags-panel">
      <div className="tags-header">
        <h3>🏷️ Tags</h3>
      </div>

      {error && <div className="error">{error}</div>}

      <form onSubmit={createTag} className="create-tag-form">
        <input
          type="text"
          value={newTagName}
          onChange={(e) => setNewTagName(e.target.value)}
          placeholder="Create new tag..."
          className="tag-input"
        />
        <button type="submit" className="btn-create-tag">Create</button>
      </form>

      {loading ? (
        <div className="loading">Loading tags...</div>
      ) : (
        <div className="tags-list">
          <h4>Available Tags:</h4>
          <div className="tags-grid">
            {tags.map((tag) => (
              <div key={tag.id} className="tag-item-wrapper">
                <button
                  onClick={() => addTagToTranscript(tag.id)}
                  className="tag-item"
                  style={{ backgroundColor: tag.color || '#e0e0e0' }}
                >
                  {tag.name}
                </button>
                <button
                  className="tag-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation()
                    deleteTag(tag.id)
                  }}
                  title="Delete tag"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          {transcriptTags.length > 0 && (
            <div className="transcript-tags-section">
              <h4>Tags on this transcript:</h4>
              <div className="tags-grid">
                {transcriptTags.map((tag) => (
                  <div key={tag.id} className="tag-item-wrapper">
                    <span
                      className="tag-item active"
                      style={{ backgroundColor: tag.color || '#4CAF50' }}
                    >
                      {tag.name}
                    </span>
                    <button
                      className="tag-remove-btn"
                      onClick={() => removeTagFromTranscript(tag.id)}
                      title="Remove tag from transcript"
                    >
                      ×
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default TagsPanel
