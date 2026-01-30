import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './TranscriptsList.css'

const API_URL = 'http://localhost:8000'

function TranscriptsList({ user, onSelectTranscript }) {
  const [transcripts, setTranscripts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    loadTranscripts()
  }, [])

  const loadTranscripts = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/transcripts`, {
        params: {
          user_id: user.user_id,
          limit: 50
        }
      })
      setTranscripts(response.data.transcripts)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load transcripts')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return <div className="loading">Loading transcripts...</div>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  return (
    <div className="transcripts-list">
      <h2>My Transcripts</h2>
      {transcripts.length === 0 ? (
        <div className="empty-state">
          <p>No transcripts yet. Start by transcribing an audio or video file.</p>
        </div>
      ) : (
        <div className="transcripts-grid">
          {transcripts.map((transcript) => (
            <div
              key={transcript.id}
              className="transcript-card"
              onClick={() => onSelectTranscript && onSelectTranscript(transcript)}
            >
              <div className="card-header">
                <h3>{transcript.source_file || transcript.source_url || 'Untitled'}</h3>
                <span className="language-badge">{transcript.language}</span>
              </div>
              <div className="card-content">
                <p>{transcript.text.substring(0, 200)}...</p>
              </div>
              <div className="card-footer">
                <span className="date">
                  {new Date(transcript.created_at).toLocaleDateString()}
                </span>
                <span className="document-id">ID: {transcript.document_id.substring(0, 8)}...</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default TranscriptsList
