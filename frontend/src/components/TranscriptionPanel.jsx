import React, { useState } from 'react'
import axios from 'axios'
import './TranscriptionPanel.css'

const API_URL = 'http://localhost:8000'

function TranscriptionPanel({ user, onTranscriptionComplete }) {
  const [inputType, setInputType] = useState('file') // 'file' or 'url'
  const [selectedFile, setSelectedFile] = useState(null)
  const [url, setUrl] = useState('')
  const [language, setLanguage] = useState('auto')
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleFileChange = (e) => {
    setSelectedFile(e.target.files[0])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setProcessing(true)

    try {
      let response

      if (inputType === 'file') {
        if (!selectedFile) {
          setError('Please select a file')
          setProcessing(false)
          return
        }

        const formData = new FormData()
        formData.append('file', selectedFile)
        formData.append('language', language)
        formData.append('user_id', user.user_id)
        formData.append('enable_preprocessing', 'true')
        formData.append('enable_validation', 'true')
        formData.append('paragraph_format', 'true')

        response = await axios.post(`${API_URL}/api/transcribe/file`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
      } else {
        if (!url.trim()) {
          setError('Please enter a URL')
          setProcessing(false)
          return
        }

        const formData = new FormData()
        formData.append('url', url)
        formData.append('language', language)
        formData.append('user_id', user.user_id)
        formData.append('enable_preprocessing', 'true')
        formData.append('enable_validation', 'true')
        formData.append('paragraph_format', 'true')

        response = await axios.post(`${API_URL}/api/transcribe/url`, formData)
      }

      setResult(response.data)
      if (onTranscriptionComplete) {
        onTranscriptionComplete(response.data)
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Transcription failed')
    } finally {
      setProcessing(false)
    }
  }

  return (
    <div className="transcription-panel">
      <h2>Transcribe Audio/Video</h2>

      <form onSubmit={handleSubmit}>
        <div className="input-type-toggle">
          <button
            type="button"
            className={inputType === 'file' ? 'active' : ''}
            onClick={() => setInputType('file')}
          >
            📁 File
          </button>
          <button
            type="button"
            className={inputType === 'url' ? 'active' : ''}
            onClick={() => setInputType('url')}
          >
            🔗 URL
          </button>
        </div>

        {inputType === 'file' ? (
          <div className="form-group">
            <label>Select Audio/Video File</label>
            <input
              type="file"
              accept="audio/*,video/*"
              onChange={handleFileChange}
              disabled={processing}
            />
            {selectedFile && (
              <div className="file-info">Selected: {selectedFile.name}</div>
            )}
          </div>
        ) : (
          <div className="form-group">
            <label>Enter URL (YouTube, Podcast, etc.)</label>
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://youtube.com/watch?v=..."
              disabled={processing}
            />
          </div>
        )}

        <div className="form-group">
          <label>Language (or Auto-detect)</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={processing}
          >
            <option value="auto">Auto-detect</option>
            <option value="en">English</option>
            <option value="hi">Hindi</option>
            <option value="te">Telugu</option>
            <option value="ta">Tamil</option>
            <option value="fr">French</option>
            <option value="es">Spanish</option>
          </select>
        </div>

        {error && <div className="error">{error}</div>}

        <button type="submit" disabled={processing} className="submit-btn">
          {processing ? 'Transcribing...' : 'Start Transcription'}
        </button>
      </form>

      {result && (
        <div className="result">
          <h3>Transcription Result</h3>
          <div className="result-text">{result.text}</div>
          <div className="result-meta">
            <span>Language: {result.language}</span>
            {result.document_id && <span>Document ID: {result.document_id}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

export default TranscriptionPanel
