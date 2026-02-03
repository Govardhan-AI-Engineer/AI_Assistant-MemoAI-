import React from 'react'
import './NoteContentModal.css'

function NoteContentModal({ note, isOpen, onClose }) {
  if (!isOpen || !note) return null

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{note.note_type === 'summary' ? '📄 Summary' : '🔑 Key Points'}</h3>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        <div className="modal-body">
          {note.note_type === 'key_points' ? (
            <FormattedKeyPoints content={note.translated_content || note.content} />
          ) : (
            <div className="note-content-text">{note.translated_content || note.content}</div>
          )}
        </div>
        <div className="modal-footer">
          <span className="note-date">
            Created: {new Date(note.created_at).toLocaleString()}
          </span>
        </div>
      </div>
    </div>
  )
}

// Component to format key points as a list
function FormattedKeyPoints({ content }) {
  const formatKeyPoints = (text) => {
    if (!text) return []
    
    const lines = text.split('\n').filter(line => line.trim())
    const items = []
    
    lines.forEach(line => {
      const trimmed = line.trim()
      const numberedMatch = trimmed.match(/^\d+[\.\)]\s*(.+)$/)
      const bulletMatch = trimmed.match(/^[-•*]\s*(.+)$/)
      
      if (numberedMatch) {
        items.push(numberedMatch[1])
      } else if (bulletMatch) {
        items.push(bulletMatch[1])
      } else if (trimmed.length > 0 && !trimmed.match(/^(Key Points|Points|Summary)/i)) {
        items.push(trimmed)
      }
    })
    
    return items.length > 0 ? items : [text]
  }
  
  const keyPoints = formatKeyPoints(content)
  
  return (
    <ul className="key-points-list-modal">
      {keyPoints.map((point, index) => (
        <li key={index}>{point}</li>
      ))}
    </ul>
  )
}

export default NoteContentModal
