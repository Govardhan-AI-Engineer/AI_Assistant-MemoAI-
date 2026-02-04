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

function NotesPanel({ user, transcriptId, targetLanguage = null, onTranscriptSelect = null }) {
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [selectedLanguage, setSelectedLanguage] = useState(targetLanguage || 'auto')
  const [selectedNote, setSelectedNote] = useState(null)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [deleting, setDeleting] = useState(null)
  const [transcripts, setTranscripts] = useState([])
  const [selectedTranscriptId, setSelectedTranscriptId] = useState(transcriptId || null)
  const [loadingTranscripts, setLoadingTranscripts] = useState(false)

  // Load transcripts list on mount
  useEffect(() => {
    loadTranscripts()
  }, [])

  // Update selected transcript when prop changes
  useEffect(() => {
    if (transcriptId) {
      setSelectedTranscriptId(transcriptId)
    }
  }, [transcriptId])

  // Load notes only when transcript changes (NOT when language changes)
  useEffect(() => {
    if (selectedTranscriptId) {
      loadNotes()
    } else {
      setNotes([])
    }
  }, [selectedTranscriptId]) // Removed selectedLanguage from dependencies

  // When language changes, just update the state (don't reload/translate notes)
  const handleLanguageChange = (newLanguage) => {
    setSelectedLanguage(newLanguage)
    // Don't reload notes - notes are shown in their original language
    // User must click "Generate Summary" or "Generate Key Points" to generate in selected language
  }

  const loadTranscripts = async () => {
    try {
      setLoadingTranscripts(true)
      const response = await axios.get(`${API_URL}/api/transcripts`, {
        params: {
          user_id: user.user_id,
          limit: 100
        }
      })
      setTranscripts(response.data.transcripts || [])
    } catch (err) {
      console.error('Failed to load transcripts:', err)
    } finally {
      setLoadingTranscripts(false)
    }
  }

  const loadNotes = async () => {
    if (!selectedTranscriptId) {
      setNotes([])
      return
    }

    try {
      setLoading(true)
      const params = {
        user_id: user.user_id,
        transcript_id: selectedTranscriptId
      }
      
      // DON'T pass target_language - show notes in their original language
      // Notes will only be generated in selected language when user clicks generate buttons
      
      const response = await axios.get(`${API_URL}/api/notes`, { params })
      setNotes(response.data.notes || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load notes')
    } finally {
      setLoading(false)
    }
  }

  const generateNote = async (noteType, forceRegenerate = false) => {
    if (!selectedTranscriptId) {
      setError('Please select a transcript first')
      return
    }

    if (!selectedLanguage || selectedLanguage === 'auto') {
      setError('Please select a target language for note generation')
      return
    }

    try {
      setGenerating(true)
      setError('')
      const formData = new FormData()
      formData.append('transcript_id', selectedTranscriptId)
      formData.append('user_id', user.user_id)
      formData.append('note_type', noteType)
      formData.append('force_regenerate', forceRegenerate)
      
      // CRITICAL: Always send target_language - notes will be generated in this language
      // This ensures notes match transcription meaning in the selected language
      formData.append('target_language', selectedLanguage)

      const response = await axios.post(`${API_URL}/api/notes/generate`, formData)
      
      // Reload notes to get newly generated notes in target language
      await loadNotes()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to generate note')
    } finally {
      setGenerating(false)
    }
  }

  const handleTranscriptSelect = (e) => {
    const newTranscriptId = parseInt(e.target.value)
    setSelectedTranscriptId(newTranscriptId)
    setNotes([]) // Clear notes when transcript changes
    
    // Notify parent if callback provided
    if (onTranscriptSelect && newTranscriptId) {
      const selectedTranscript = transcripts.find(t => t.id === newTranscriptId)
      if (selectedTranscript) {
        onTranscriptSelect(selectedTranscript)
      }
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

  const formatTranscriptName = (transcript) => {
    let name = transcript.source_file || transcript.source_url || 'Untitled'
    if (name.includes('/') || name.includes('\\')) {
      name = name.split(/[/\\]/).pop()
    }
    name = name.replace(/\.[^/.]+$/, '')
    return name || 'Untitled Transcript'
  }

  return (
    <div className="notes-panel">
      <div className="notes-header">
        <h3>📝 Notes</h3>
        <div className="notes-controls">
          <div className="transcript-selector">
            <label>Select Transcript:</label>
            <select
              value={selectedTranscriptId || ''}
              onChange={handleTranscriptSelect}
              disabled={generating || loadingTranscripts}
            >
              <option value="">-- Select a transcript --</option>
              {transcripts.map((transcript) => (
                <option key={transcript.id} value={transcript.id}>
                  {formatTranscriptName(transcript)} ({transcript.language || 'auto'})
                </option>
              ))}
            </select>
          </div>
          <div className="language-selector">
            <label>Target Language:</label>
            <select
              value={selectedLanguage}
              onChange={(e) => handleLanguageChange(e.target.value)}
              disabled={generating || !selectedTranscriptId}
            >
              <option value="auto">Original Language</option>
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="te">Telugu</option>
              <option value="ta">Tamil</option>
              <option value="kn">Kannada</option>
              <option value="ml">Malayalam</option>
              <option value="bn">Bengali</option>
              <option value="mr">Marathi</option>
              <option value="gu">Gujarati</option>
              <option value="pa">Punjabi</option>
              <option value="fr">French</option>
              <option value="es">Spanish</option>
              <option value="de">German</option>
              <option value="it">Italian</option>
              <option value="pt">Portuguese</option>
              <option value="zh">Chinese</option>
              <option value="ja">Japanese</option>
              <option value="ko">Korean</option>
              <option value="ar">Arabic</option>
            </select>
          </div>
          <div className="note-actions">
            <button
              onClick={() => generateNote('summary')}
              disabled={generating || !selectedTranscriptId || !selectedLanguage || selectedLanguage === 'auto'}
              className="btn-generate"
              title={!selectedTranscriptId ? 'Select a transcript first' : (!selectedLanguage || selectedLanguage === 'auto') ? 'Select a target language first' : 'Generate summary in selected language'}
            >
              {generating ? 'Generating...' : 'Generate Summary'}
            </button>
            <button
              onClick={() => generateNote('key_points')}
              disabled={generating || !selectedTranscriptId || !selectedLanguage || selectedLanguage === 'auto'}
              className="btn-generate"
              title={!selectedTranscriptId ? 'Select a transcript first' : (!selectedLanguage || selectedLanguage === 'auto') ? 'Select a target language first' : 'Generate key points in selected language'}
            >
              {generating ? 'Generating...' : 'Generate Key Points'}
            </button>
          </div>
        </div>
      </div>

      {error && <div className="error">{error}</div>}

      {!selectedTranscriptId ? (
        <div className="empty-state" style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
          <p>Please select a transcript to view or generate notes.</p>
        </div>
      ) : loading ? (
        <div className="loading">Loading notes...</div>
      ) : (
        <div className="notes-list">
          {notes.length === 0 ? (
            <div className="empty-state">
              <p>No notes yet. Select a target language and click "Generate Summary" or "Generate Key Points" to create notes in your selected language.</p>
              <p style={{ marginTop: '0.5rem', fontSize: '0.9em', color: '#888' }}>
                Notes will be generated directly in the selected language (not translated).
              </p>
            </div>
          ) : (
            notes.map((note) => (
              <div key={note.id} className="note-card">
                <div className="note-header">
                  <span className="note-type">
                    {note.note_type === 'summary' ? '📄 Summary' : '🔑 Key Points'}
                    {note.language && note.language !== 'auto' && (
                      <span className="note-language-badge" title={`Language: ${note.language}`}>
                        {' '}({note.language})
                      </span>
                    )}
                  </span>
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
                      {note.content && note.content.length > 150 && (
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
