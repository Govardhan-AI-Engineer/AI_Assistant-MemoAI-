import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './TranscriptsList.css'

const API_URL = 'http://localhost:8000'

function TranscriptsList({ user, onSelectTranscript, activeView = 'all' }) {
  const [transcripts, setTranscripts] = useState([])
  const [filteredTranscripts, setFilteredTranscripts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [deletingId, setDeletingId] = useState(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [filterLanguage, setFilterLanguage] = useState('all')

  useEffect(() => {
    loadTranscripts()
  }, [])

  useEffect(() => {
    filterTranscripts()
  }, [searchQuery, filterLanguage, transcripts, activeView])

  const loadTranscripts = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/transcripts`, {
        params: {
          user_id: user.user_id,
          limit: 50
        }
      })
      setTranscripts(response.data.transcripts || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load transcripts')
    } finally {
      setLoading(false)
    }
  }

  const filterTranscripts = () => {
    let filtered = [...transcripts]

    // Only apply filters if not in 'all' view
    if (activeView === 'search') {
      // Apply search filter
      if (searchQuery.trim()) {
        const query = searchQuery.toLowerCase()
        filtered = filtered.filter(t => 
          (t.text && t.text.toLowerCase().includes(query)) ||
          (t.source_file && t.source_file.toLowerCase().includes(query)) ||
          (t.source_url && t.source_url.toLowerCase().includes(query))
        )
      } else {
        // If search view but no query, show all
        filtered = transcripts
      }
    } else if (activeView === 'filter') {
      // Apply language filter
      if (filterLanguage !== 'all') {
        filtered = filtered.filter(t => t.language === filterLanguage)
      }
    }
    // If activeView === 'all', show all transcripts (no filtering)

    setFilteredTranscripts(filtered)
  }

  const getUniqueLanguages = () => {
    const languages = new Set(transcripts.map(t => t.language).filter(Boolean))
    return Array.from(languages).sort()
  }

  const formatTranscriptName = (transcript) => {
    let name = transcript.source_file || transcript.source_url || 'Untitled'
    
    // If it's a file path, extract just the filename
    if (name.includes('/') || name.includes('\\')) {
      name = name.split(/[/\\]/).pop()
    }
    
    // Remove file extension
    name = name.replace(/\.[^/.]+$/, '')
    
    // Clean up: replace underscores/hyphens with spaces, remove special chars
    name = name
      .replace(/[-_]/g, ' ')
      .replace(/[^a-zA-Z0-9\s]/g, '')
      .trim()
    
    // Capitalize first letter of each word
    name = name
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ')
      .trim()
    
    return name || 'Untitled Transcript'
  }

  const handleDelete = async (transcriptId, e) => {
    e.stopPropagation() // Prevent card click
    
    if (!window.confirm('Are you sure you want to delete this transcript? This will also delete all translations, notes, tags, and embeddings associated with it.')) {
      return
    }

    try {
      setDeletingId(transcriptId)
      await axios.delete(`${API_URL}/api/transcripts/${transcriptId}`, {
        params: { user_id: user.user_id }
      })
      await loadTranscripts() // Reload list
    } catch (err) {
      alert(`Failed to delete transcript: ${err.response?.data?.detail || 'Unknown error'}`)
    } finally {
      setDeletingId(null)
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
      <div className="list-header">
        <h2>My Transcripts</h2>
        <div className="list-subtitle">Parsed & synced from your sources</div>
      </div>
      
      {/* Search and Filter Controls */}
      {transcripts.length > 0 && activeView === 'search' && (
        <div className="search-filter-controls">
          <div className="search-box">
            <input
              type="text"
              placeholder="Search transcripts..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="search-input"
            />
          </div>
        </div>
      )}
      
      {transcripts.length > 0 && activeView === 'filter' && (
        <div className="search-filter-controls">
          <div className="filter-box">
            <label>Language:</label>
            <select
              value={filterLanguage}
              onChange={(e) => setFilterLanguage(e.target.value)}
              className="filter-select"
            >
              <option value="all">All Languages</option>
              {getUniqueLanguages().map(lang => (
                <option key={lang} value={lang}>{lang.toUpperCase()}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      {transcripts.length === 0 ? (
        <div className="empty-state">
          <p>No transcripts yet. Start by transcribing an audio or video file.</p>
        </div>
      ) : (activeView === 'all' ? transcripts : filteredTranscripts).length === 0 ? (
        <div className="empty-state">
          <p>No transcripts match your {activeView === 'search' ? 'search' : activeView === 'filter' ? 'filter' : ''} criteria.</p>
        </div>
      ) : (
        <div className="transcripts-grid">
          {(activeView === 'all' ? transcripts : filteredTranscripts).map((transcript) => (
            <div
              key={transcript.id}
              className="transcript-card"
              onClick={() => onSelectTranscript && onSelectTranscript(transcript)}
            >
              <div className="card-header">
                <h3>{formatTranscriptName(transcript)}</h3>
                <div className="header-actions">
                  <span className="language-badge">{transcript.language}</span>
                  <button
                    className="delete-btn"
                    onClick={(e) => handleDelete(transcript.id, e)}
                    disabled={deletingId === transcript.id}
                    title="Delete transcript"
                  >
                    {deletingId === transcript.id ? '⏳' : '🗑️'}
                  </button>
                </div>
              </div>
              <div className="card-content">
                <p>{transcript.text.substring(0, 200)}...</p>
              </div>
              <div className="card-footer">
                <div className="footer-info">
                  <span className="date">
                    {new Date(transcript.created_at).toLocaleDateString()}
                  </span>
                  <span className="document-id">ID: {transcript.document_id.substring(0, 8)}...</span>
                </div>
                {/* Add tags display if transcript has tags */}
                {transcript.tags && transcript.tags.length > 0 && (
                  <div className="transcript-tags">
                    {transcript.tags.map((tag) => (
                      <span key={tag.id} className="tag-badge" style={{ backgroundColor: tag.color || '#e0e0e0' }}>
                        {tag.name}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default TranscriptsList
