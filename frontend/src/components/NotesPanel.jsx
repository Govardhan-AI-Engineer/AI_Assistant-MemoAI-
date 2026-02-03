import React, { useState, useEffect } from 'react'
import axios from 'axios'
import NoteContentModal from './NoteContentModal'
import './NotesPanel.css'

const API_URL = 'http://localhost:8000'

// Component to format key points as a list
function FormattedKeyPoints({ content, className = 'key-points-list' }) {
  // Parse content to extract list items
  const formatKeyPoints = (text) => {
    if (!text) return []
    
    // Split by common list markers
    const lines = text.split('\n').filter(line => line.trim())
    const items = []
    
    lines.forEach(line => {
      const trimmed = line.trim()
      // Match numbered lists (1., 2., etc.)
      const numberedMatch = trimmed.match(/^\d+[\.\)]\s*(.+)$/)
      // Match bullet points (-, •, *, etc.)
      const bulletMatch = trimmed.match(/^[-•*]\s*(.+)$/)
      
      if (numberedMatch) {
        items.push(numberedMatch[1])
      } else if (bulletMatch) {
        items.push(bulletMatch[1])
      } else if (trimmed.length > 0 && !trimmed.match(/^(Key Points|Points|Summary)/i)) {
        // If it's not a header, treat as a point
        items.push(trimmed)
      }
    })
    
    return items.length > 0 ? items : [text] // Fallback to original text if no list found
  }
  
  const keyPoints = formatKeyPoints(content)
  
  return (
    <ul className={className}>
      {keyPoints.map((point, index) => (
        <li key={index}>{point}</li>
      ))}
    </ul>
  )
}

function NotesPanel({ user, transcriptId, targetLanguage = null }) {
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [selectedLanguage, setSelectedLanguage] = useState(targetLanguage || 'auto')
  const [selectedNote, setSelectedNote] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [deleting, setDeleting] = useState(null)

  useEffect(() => {
    if (transcriptId) {
      loadNotes()
    }
  }, [transcriptId])

  const loadNotes = async () => {
    try {
      setLoading(true)
      const response = await axios.get(`${API_URL}/api/notes`, {
        params: {
          user_id: user.user_id,
          transcript_id: transcriptId
        }
      })
      setNotes(response.data.notes || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load notes')
    } finally {
      setLoading(false)
    }
  }

  const generateNote = async (noteType, forceRegenerate = false) => {
    try {
      setGenerating(true)
      setError('')
      const formData = new FormData()
      formData.append('transcript_id', transcriptId)
      formData.append('user_id', user.user_id)
      formData.append('note_type', noteType)
      formData.append('force_regenerate', forceRegenerate)
      
      // Add target language if specified (not 'auto')
      // Note: Notes are canonical (generated once in original language)
      // This language is only for display/translation purposes
      if (selectedLanguage && selectedLanguage !== 'auto') {
        formData.append('target_language', selectedLanguage)
      }

      const response = await axios.post(`${API_URL}/api/notes/generate`, formData)
      
      // Reload notes
      await loadNotes()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate note')
    } finally {
      setGenerating(false)
    }
  }

  const deleteNote = async (noteId) => {
    if (!window.confirm('Are you sure you want to delete this note?')) {
      return
    }

    try {
      setDeleting(noteId)
      await axios.delete(`${API_URL}/api/notes/${noteId}`, {
        params: { user_id: user.user_id }
      })
      await loadNotes()
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to delete note')
    } finally {
      setDeleting(null)
    }
  }

  const openNoteModal = (note) => {
    setSelectedNote(note)
    setIsModalOpen(true)
  }

  const closeNoteModal = () => {
    setIsModalOpen(false)
    setSelectedNote(null)
  }

  // Truncate text for preview
  const truncateText = (text, maxLength = 150) => {
    if (!text) return ''
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }
  
  // Update selected language when targetLanguage prop changes
  useEffect(() => {
    if (targetLanguage) {
      setSelectedLanguage(targetLanguage)
    }
  }, [targetLanguage])

  if (!transcriptId) {
    return (
      <div className="notes-panel">
        <p>Select a transcript to view or generate notes.</p>
      </div>
    )
  }

  return (
    <div className="notes-panel">
      <div className="notes-header">
        <h3>📝 Notes</h3>
        <div className="notes-controls">
          <div className="language-selector">
            <label>Note Language:</label>
            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              disabled={generating}
            >
              <option value="auto">Original Language</option>
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="te">Telugu</option>
              <option value="ta">Tamil</option>
              <option value="fr">French</option>
              <option value="es">Spanish</option>
              <option value="de">German</option>
              <option value="it">Italian</option>
              <option value="pt">Portuguese</option>
            </select>
          </div>
          <div className="note-actions">
            <button
              onClick={() => generateNote('summary')}
              disabled={generating}
              className="btn-generate"
            >
              {generating ? 'Generating...' : 'Generate Summary'}
            </button>
            <button
              onClick={() => generateNote('key_points')}
              disabled={generating}
              className="btn-generate"
            >
              {generating ? 'Generating...' : 'Generate Key Points'}
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {loading ? (
        <div className="loading">Loading notes...</div>
      ) : (
        <div className="notes-list">
          {notes.length === 0 ? (
            <div className="empty-state">
              <p>No notes yet. Generate a summary or key points to get started.</p>
            </div>
          ) : (
            notes.map((note) => (
              <div key={note.id} className="note-card">
                <div className="note-header">
                  <span className="note-type">{note.note_type === 'summary' ? '📄 Summary' : '🔑 Key Points'}</span>
                  <div className="note-header-actions">
                    <span className="note-date">
                      {new Date(note.created_at).toLocaleDateString()}
                    </span>
                    <button
                      className="btn-delete-note"
                      onClick={() => deleteNote(note.id)}
                      disabled={deleting === note.id}
                      title="Delete note"
                    >
                      {deleting === note.id ? '⏳' : '🗑️'}
                    </button>
                  </div>
                </div>
                <div 
                  className={`note-content-preview ${note.note_type === 'key_points' ? 'key-points' : ''}`}
                  onClick={() => openNoteModal(note)}
                >
                  {note.note_type === 'key_points' ? (
                    <div className="key-points-preview">
                      <FormattedKeyPoints content={truncateText(note.content)} />
                      <div className="view-full">Click to view full content →</div>
                    </div>
                  ) : (
                    <div>
                      <p>{truncateText(note.content)}</p>
                      {note.content.length > 150 && (
                        <div className="view-full">Click to view full content →</div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      <NoteContentModal
        note={selectedNote}
        isOpen={isModalOpen}
        onClose={closeNoteModal}
      />
    </div>
  )
}

export default NotesPanel
