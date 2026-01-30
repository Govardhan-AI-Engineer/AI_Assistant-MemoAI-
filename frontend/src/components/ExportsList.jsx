import React, { useState, useEffect } from 'react'
import axios from 'axios'
import './ExportsList.css'

const API_URL = 'http://localhost:8000'

function ExportsList({ user, transcriptId = null }) {
  const [exports, setExports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filterType, setFilterType] = useState('all') // 'all', 'subtitle', 'document', 'audio'

  useEffect(() => {
    loadExports()
  }, [transcriptId, filterType])

  const loadExports = async () => {
    try {
      setLoading(true)
      const params = {
        user_id: user.user_id,
        ...(transcriptId && { transcript_id: transcriptId }),
        ...(filterType !== 'all' && { file_type: filterType })
      }
      
      const response = await axios.get(`${API_URL}/api/exports`, { params })
      setExports(response.data.exports)
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load exports')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async (exportItem, fileName) => {
    try {
      let url
      // Use ID if available (database entry), otherwise use file path
      if (exportItem.id) {
        url = `${API_URL}/api/exports/${exportItem.id}/download?user_id=${user.user_id}`
      } else {
        // File not in database, use path-based download
        url = `${API_URL}/api/exports/file/${encodeURIComponent(exportItem.file_path)}/download?user_id=${user.user_id}`
      }
      
      const response = await axios.get(url, { responseType: 'blob' })
      
      // Create download link
      const blobUrl = window.URL.createObjectURL(new Blob([response.data]))
      const link = document.createElement('a')
      link.href = blobUrl
      link.setAttribute('download', fileName)
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(blobUrl)
    } catch (err) {
      alert(`Download failed: ${err.response?.data?.detail || 'Unknown error'}`)
    }
  }

  const formatFileSize = (bytes) => {
    if (!bytes) return 'Unknown'
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getFileIcon = (fileType, fileFormat) => {
    if (fileType === 'subtitle') return '📝'
    if (fileType === 'document') {
      if (fileFormat === 'json') return '📋'
      if (fileFormat === 'md') return '📄'
      return '📄'
    }
    if (fileType === 'audio') return '🔊'
    return '📁'
  }

  const groupByType = (exports) => {
    const grouped = {
      subtitle: [],
      document: [],
      audio: []
    }
    
    exports.forEach(exp => {
      if (grouped[exp.file_type]) {
        grouped[exp.file_type].push(exp)
      }
    })
    
    return grouped
  }

  if (loading) {
    return <div className="loading">Loading exports...</div>
  }

  if (error) {
    return <div className="error">{error}</div>
  }

  const grouped = groupByType(exports)

  return (
    <div className="exports-list">
      <div className="exports-header">
        <h2>📦 My Exports</h2>
        <div className="filter-controls">
          <label>Filter:</label>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="filter-select"
          >
            <option value="all">All Types</option>
            <option value="subtitle">Subtitles</option>
            <option value="document">Documents</option>
            <option value="audio">Audio</option>
          </select>
        </div>
      </div>

      {exports.length === 0 ? (
        <div className="empty-state">
          <p>No exports yet. Export subtitles, documents, or audio from your transcripts.</p>
        </div>
      ) : (
        <div className="exports-content">
          {/* Subtitles Section */}
          {grouped.subtitle.length > 0 && (filterType === 'all' || filterType === 'subtitle') && (
            <div className="export-section">
              <h3>📝 Subtitles ({grouped.subtitle.length})</h3>
              <div className="exports-grid">
                {grouped.subtitle.map((exp) => (
                  <div key={exp.id} className="export-card">
                    <div className="card-icon">{getFileIcon(exp.file_type, exp.file_format)}</div>
                    <div className="card-content">
                      <div className="card-title">{exp.file_path.split('/').pop()}</div>
                      <div className="card-meta">
                        <span className="format-badge">{exp.file_format.toUpperCase()}</span>
                        {exp.language && (
                          <span className="language-badge">{exp.language}</span>
                        )}
                        {exp.is_translated && (
                          <span className="translated-badge">Translated</span>
                        )}
                      </div>
                      <div className="card-footer">
                        <span className="file-size">{formatFileSize(exp.file_size)}</span>
                        <span className="file-date">
                          {new Date(exp.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <button
                      className="download-btn"
                      onClick={() => handleDownload(exp, exp.file_path.split('/').pop())}
                    >
                      ⬇️ Download
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Documents Section */}
          {grouped.document.length > 0 && (filterType === 'all' || filterType === 'document') && (
            <div className="export-section">
              <h3>📄 Documents ({grouped.document.length})</h3>
              <div className="exports-grid">
                {grouped.document.map((exp) => (
                  <div key={exp.id} className="export-card">
                    <div className="card-icon">{getFileIcon(exp.file_type, exp.file_format)}</div>
                    <div className="card-content">
                      <div className="card-title">{exp.file_path.split('/').pop()}</div>
                      <div className="card-meta">
                        <span className="format-badge">{exp.file_format.toUpperCase()}</span>
                        {exp.language && (
                          <span className="language-badge">{exp.language}</span>
                        )}
                        {exp.is_translated && (
                          <span className="translated-badge">Translated</span>
                        )}
                      </div>
                      <div className="card-footer">
                        <span className="file-size">{formatFileSize(exp.file_size)}</span>
                        <span className="file-date">
                          {new Date(exp.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <button
                      className="download-btn"
                      onClick={() => handleDownload(exp, exp.file_path.split('/').pop())}
                    >
                      ⬇️ Download
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Audio Section */}
          {grouped.audio.length > 0 && (filterType === 'all' || filterType === 'audio') && (
            <div className="export-section">
              <h3>🔊 Audio ({grouped.audio.length})</h3>
              <div className="exports-grid">
                {grouped.audio.map((exp) => (
                  <div key={exp.id} className="export-card">
                    <div className="card-icon">{getFileIcon(exp.file_type, exp.file_format)}</div>
                    <div className="card-content">
                      <div className="card-title">{exp.file_path.split('/').pop()}</div>
                      <div className="card-meta">
                        <span className="format-badge">{exp.file_format.toUpperCase()}</span>
                        {exp.language && (
                          <span className="language-badge">{exp.language}</span>
                        )}
                        {exp.is_translated && (
                          <span className="translated-badge">Translated</span>
                        )}
                      </div>
                      <div className="card-footer">
                        <span className="file-size">{formatFileSize(exp.file_size)}</span>
                        <span className="file-date">
                          {new Date(exp.created_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                    <button
                      className="download-btn"
                      onClick={() => handleDownload(exp, exp.file_path.split('/').pop())}
                    >
                      ⬇️ Download
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

export default ExportsList
