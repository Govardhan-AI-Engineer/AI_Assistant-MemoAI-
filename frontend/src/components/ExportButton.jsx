import React, { useState } from 'react'
import axios from 'axios'
import './ExportButton.css'

const API_URL = 'http://localhost:8000'

function ExportButton({ user, transcriptId, type, icon, label, formats, targetLanguage }) {
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [showFormatMenu, setShowFormatMenu] = useState(false)

  const handleExport = async (format) => {
    try {
      setExporting(true)
      setError('')
      setSuccess(false)
      setShowFormatMenu(false)

      const formData = new FormData()
      formData.append('transcript_id', transcriptId)
      formData.append('user_id', user.user_id)

      let response
      if (type === 'subtitle') {
        formData.append('format', format)
        formData.append('use_translated', 'false')
        response = await axios.post(`${API_URL}/api/export/subtitles`, formData)
      } else if (type === 'document') {
        formData.append('format', format)
        formData.append('use_translated', 'false')
        response = await axios.post(`${API_URL}/api/export/documents`, formData)
      } else if (type === 'audio') {
        formData.append('format', format)
        // Use current translation language as target language for audio
        // Audio MUST be generated from translated text
        if (targetLanguage) {
          formData.append('target_language', targetLanguage)
          formData.append('use_translated', 'true')
        } else {
          // If no translation language provided, default to English
          // But this should ideally not happen - user should translate first
          formData.append('target_language', 'en')
          formData.append('use_translated', 'true')
        }
        response = await axios.post(`${API_URL}/api/export/audio`, formData)
      }

      if (response.data) {
        setSuccess(true)
        setTimeout(() => setSuccess(false), 3000)
        // Show success message
        alert(`${label} exported successfully! File saved to exports folder.`)
      }
    } catch (err) {
      setError(err.response?.data?.detail || `Failed to export ${label}`)
      setTimeout(() => setError(''), 5000)
    } finally {
      setExporting(false)
    }
  }

  const formatLabels = {
    'srt': 'SRT',
    'vtt': 'VTT',
    'both': 'Both (SRT + VTT)',
    'md': 'Markdown',
    'txt': 'Plain Text',
    'json': 'JSON',
    'mp3': 'MP3',
    'wav': 'WAV'
  }

  return (
    <div className="export-button-wrapper">
      <button
        className={`export-btn ${type} ${exporting ? 'exporting' : ''} ${success ? 'success' : ''}`}
        onClick={() => {
          if (formats.length === 1) {
            handleExport(formats[0])
          } else {
            setShowFormatMenu(!showFormatMenu)
          }
        }}
        disabled={exporting}
        title={`Export ${label}`}
      >
        <span className="export-icon">{icon}</span>
        <span className="export-label">{label}</span>
        {exporting && <span className="export-spinner">⏳</span>}
        {success && <span className="export-check">✓</span>}
        {formats.length > 1 && !exporting && !success && (
          <span className="export-arrow">▼</span>
        )}
      </button>
      
      {showFormatMenu && formats.length > 1 && (
        <div className="format-menu">
          {formats.map((format) => (
            <button
              key={format}
              className="format-option"
              onClick={() => handleExport(format)}
            >
              {formatLabels[format] || format}
            </button>
          ))}
        </div>
      )}

      {error && (
        <div className="export-error">{error}</div>
      )}
    </div>
  )
}

export default ExportButton