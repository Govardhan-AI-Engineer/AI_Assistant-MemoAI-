import React, { useState } from 'react'
import axios from 'axios'
import ExportButton from './ExportButton'
import './TranslationPanel.css'

const API_URL = 'http://localhost:8000'

function TranslationPanel({ user, transcript, onLanguageChange, onNavigateToNotes }) {
  const [targetLanguage, setTargetLanguage] = useState('en')
  const [provider, setProvider] = useState('auto')
  const [granularity, setGranularity] = useState('whole_text')
  const [enableRetranslation, setEnableRetranslation] = useState(false)
  const [translating, setTranslating] = useState(false)
  const [translation, setTranslation] = useState(null)
  const [error, setError] = useState('')

  const handleTranslate = async (e) => {
    e.preventDefault()
    // Support both 'id' (from database) and 'transcript_id' (from transcription response)
    const transcriptId = transcript?.transcript_id || transcript?.id
    if (!transcript || !transcriptId) {
      setError('No transcript available')
      return
    }

    setError('')
    setTranslating(true)

    try {
      const formData = new FormData()
      formData.append('transcript_id', transcriptId)
      formData.append('target_language', targetLanguage)
      formData.append('user_id', user.user_id)
      formData.append('preferred_provider', provider === 'auto' ? '' : provider)
      formData.append('granularity', granularity)
      formData.append('enable_paragraph_retranslation', enableRetranslation.toString())

      const response = await axios.post(`${API_URL}/api/translate`, formData)
      setTranslation(response.data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Translation failed')
    } finally {
      setTranslating(false)
    }
  }

  return (
    <div className="translation-panel">
      <h2>Translate Transcript</h2>

      <form onSubmit={handleTranslate}>
        <div className="form-row">
          <div className="form-group">
            <label>Target Language</label>
            <select
              value={targetLanguage}
              onChange={(e) => {
                setTargetLanguage(e.target.value)
                if (onLanguageChange) {
                  onLanguageChange(e.target.value)
                }
              }}
              disabled={translating}
            >
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="te">Telugu</option>
              <option value="ta">Tamil</option>
              <option value="fr">French</option>
              <option value="es">Spanish</option>
              <option value="de">German</option>
            </select>
          </div>

          <div className="form-group">
            <label>Translation Provider</label>
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              disabled={translating}
            >
              <option value="auto">Auto (Default Priority)</option>
              <option value="google">Google Translate</option>
              <option value="libre">LibreTranslate</option>
              <option value="deepl">DeepL</option>
              <option value="ai">AI Translation (Groq)</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Translation Mode</label>
            <select
              value={granularity}
              onChange={(e) => setGranularity(e.target.value)}
              disabled={translating}
            >
              <option value="whole_text">Whole Text</option>
              <option value="paragraph">Paragraph-wise</option>
              <option value="line_by_line">Line-by-line</option>
            </select>
          </div>
        </div>

        <div className="form-group checkbox-group">
          <label>
            <input
              type="checkbox"
              checked={enableRetranslation}
              onChange={(e) => setEnableRetranslation(e.target.checked)}
              disabled={translating}
            />
            Enable paragraph-level re-translation for quality refinement
          </label>
        </div>

        {error && <div className="error">{error}</div>}

        <button type="submit" disabled={translating} className="submit-btn">
          {translating ? 'Translating...' : 'Translate'}
        </button>
      </form>

      {translation && (
        <div className="translation-result">
          <h3>Translation Result</h3>
          <div className="translation-text">{translation.translated_text}</div>
          <div className="translation-meta">
            <span>Provider: {translation.provider || 'unknown'}</span>
            <span>Language: {translation.target_language}</span>
          </div>
          
          {/* Generate Notes Section */}
          {transcript && (
            <div className="generate-notes-section">
              <h4>Generate Notes</h4>
              <p className="notes-description">
                Generate summary and key points in <strong>{translation.target_language.toUpperCase()}</strong>
              </p>
              <div className="notes-buttons">
                <button
                  className="btn-generate-notes"
                  onClick={() => {
                    // Notify parent to switch to notes tab with target language
                    if (onLanguageChange) {
                      onLanguageChange(translation.target_language)
                    }
                    // Navigate to notes tab
                    if (onNavigateToNotes) {
                      onNavigateToNotes(translation.target_language)
                    }
                  }}
                >
                  📝 Generate Notes
                </button>
              </div>
            </div>
          )}
          
          {transcript && (
            <div className="export-actions">
              <h4>Export Options</h4>
              <div className="export-buttons">
                <ExportButton
                  user={user}
                  transcriptId={transcript.transcript_id || transcript.id}
                  type="subtitle"
                  icon="📄"
                  label="Subtitles"
                  formats={['srt', 'vtt', 'both']}
                />
                <ExportButton
                  user={user}
                  transcriptId={transcript.transcript_id || transcript.id}
                  type="document"
                  icon="📝"
                  label="Documents"
                  formats={['md', 'txt', 'json']}
                />
                <ExportButton
                  user={user}
                  transcriptId={transcript.transcript_id || transcript.id}
                  type="audio"
                  icon="🔊"
                  label="Audio"
                  formats={['mp3', 'wav']}
                  targetLanguage={translation?.target_language || targetLanguage}
                />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default TranslationPanel
