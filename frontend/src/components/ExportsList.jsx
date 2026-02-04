import React, { useState, useEffect } from 'react'
import axios from 'axios'
import ContentViewer from './ContentViewer'
import AudioPlayer from './AudioPlayer'
import './ExportsList.css'

const API_URL = 'http://localhost:8000'

function ExportsList({ user, transcriptId = null, filterType: propFilterType = 'all' }) {
  const [exports, setExports] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filterType, setFilterType] = useState(propFilterType) // 'all', 'subtitle', 'document', 'audio'
  const [viewingContent, setViewingContent] = useState(null) // { type: 'content' | 'audio', data: {...} }
  const [deletingId, setDeletingId] = useState(null)

  // Update filterType when prop changes
  useEffect(() => {
    setFilterType(propFilterType)
  }, [propFilterType])

  useEffect(() => {
    loadExports()
  }, [transcriptId, propFilterType])

  const loadExports = async () => {
    try {
      setLoading(true)
      // Always load all exports, filter on frontend
      const params = {
        user_id: user.user_id,
        ...(transcriptId && { transcript_id: transcriptId })
        // Don't filter by file_type here - we'll filter on frontend
      }
      
      const response = await axios.get(`${API_URL}/api/exports`, { params })
      setExports(response.data.exports || [])
      setError('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load exports')
      setExports([])
    } finally {
      setLoading(false)
    }
  }

  const handleView = async (exportItem) => {
    try {
      let url
      if (exportItem.id) {
        url = `${API_URL}/api/exports/${exportItem.id}/content?user_id=${user.user_id}`
      } else {
        url = `${API_URL}/api/exports/file/${encodeURIComponent(exportItem.file_path)}/content?user_id=${user.user_id}`
      }
      
      const response = await axios.get(url)
      setViewingContent({
        type: 'content',
        content: response.data.content,
        filename: response.data.filename,
        fileFormat: response.data.file_format
      })
    } catch (err) {
      alert(`Failed to load content: ${err.response?.data?.detail || 'Unknown error'}`)
    }
  }

  const handlePlayAudio = async (exportItem) => {
    try {
      let audioUrl
      if (exportItem.id) {
        audioUrl = `${API_URL}/api/exports/${exportItem.id}/download?user_id=${user.user_id}`
      } else {
        audioUrl = `${API_URL}/api/exports/file/${encodeURIComponent(exportItem.file_path)}/download?user_id=${user.user_id}`
      }
      
      setViewingContent({
        type: 'audio',
        audioUrl: audioUrl,
        filename: exportItem.file_path.split('/').pop()
      })
    } catch (err) {
      alert(`Failed to load audio: ${err.response?.data?.detail || 'Unknown error'}`)
    }
  }

  const handleDelete = async (exportItem, e) => {
    e.stopPropagation() // Prevent card click
    
    if (!window.confirm(`Are you sure you want to delete "${exportItem.file_path.split('/').pop()}"? This action cannot be undone.`)) {
      return
    }

    try {
      setDeletingId(exportItem.id || exportItem.file_path)
      if (exportItem.id) {
        await axios.delete(`${API_URL}/api/exports/${exportItem.id}`, {
          params: { user_id: user.user_id }
        })
      } else {
        await axios.delete(`${API_URL}/api/exports/file/${encodeURIComponent(exportItem.file_path)}`, {
          params: { user_id: user.user_id }
        })
      }
      await loadExports() // Reload list
    } catch (err) {
      alert(`Failed to delete file: ${err.response?.data?.detail || 'Unknown error'}`)
    } finally {
      setDeletingId(null)
    }
  }

  const handleDownload = async (exportItem, fileName) => {
    try {
      let url
      // Use ID if available (database entry), otherwise use file path
      if (exportItem.id) {
        url = `${API_URL}/api/exports/${exportItem.id}/download?user_id=${user.user_id}&force_download=true`
      } else {
        // File not in database, use path-based download
        url = `${API_URL}/api/exports/file/${encodeURIComponent(exportItem.file_path)}/download?user_id=${user.user_id}&force_download=true`
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

  const formatFileName = (filePath) => {
    if (!filePath) return 'Untitled'
    
    // Extract filename from path
    const fileName = filePath.split('/').pop() || filePath
    
    // Remove file extension for display
    const nameWithoutExt = fileName.replace(/\.[^/.]+$/, '')
    
    // Clean up the name: remove special characters, replace underscores/hyphens with spaces
    let cleaned = nameWithoutExt
      .replace(/[-_]/g, ' ')
      .replace(/[^a-zA-Z0-9\s]/g, '')
      .trim()
    
    // Capitalize first letter of each word
    cleaned = cleaned
      .split(' ')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ')
      .trim()
    
    // Truncate if too long (max 40 characters)
    if (cleaned.length > 40) {
      cleaned = cleaned.substring(0, 37) + '...'
    }
    
    // Get file extension
    const ext = fileName.split('.').pop()?.toUpperCase() || ''
    
    return cleaned || 'Untitled'
  }

  const getDisplayFileName = (filePath) => {
    const formatted = formatFileName(filePath)
    const ext = filePath.split('.').pop()?.toUpperCase() || ''
    return formatted
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

  // Filter exports based on current filterType (use propFilterType to ensure we use the latest value)
  const currentFilter = propFilterType || filterType
  const filteredExports = currentFilter === 'all' 
    ? exports 
    : exports.filter(exp => exp.file_type === currentFilter)
  
  const grouped = groupByType(filteredExports)
  
  // Check if any sections have content
  const hasContent = grouped.subtitle.length > 0 || grouped.document.length > 0 || grouped.audio.length > 0

  return (
    <div className="exports-list">
      <div className="exports-header">
        <div>
          <h2>📦 My Exports</h2>
          <div className="list-subtitle">Generated files from your transcripts</div>
        </div>
      </div>

      {exports.length === 0 ? (
        <div className="empty-state">
          <p>No exports yet. Export subtitles, documents, or audio from your transcripts.</p>
        </div>
      ) : !hasContent ? (
        <div className="empty-state">
          <p>No {currentFilter === 'all' ? '' : currentFilter.charAt(0).toUpperCase() + currentFilter.slice(1)} exports found.</p>
        </div>
      ) : (
        <div className="exports-content">
          {/* Subtitles Section */}
          {grouped.subtitle.length > 0 && (currentFilter === 'all' || currentFilter === 'subtitle') && (
            <div className="export-section">
              <h3>📝 Subtitles ({grouped.subtitle.length})</h3>
              <div className="exports-grid">
                {grouped.subtitle.map((exp) => (
                  <div key={exp.id || exp.file_path} className="export-card">
                    <div 
                      className="card-icon content-icon-clickable" 
                      onClick={() => handleView(exp)}
                      title="Click to view"
                    >
                      {getFileIcon(exp.file_type, exp.file_format)}
                    </div>
                    <div className="card-content">
                      <div className="card-title" title={exp.file_path.split('/').pop()}>
                        {getDisplayFileName(exp.file_path)}
                      </div>
                      <div className="card-meta">
                        <span className="format-badge">{exp.file_format.toUpperCase()}</span>
                        {exp.language && (
                          <span className="language-badge">{exp.language.toUpperCase()}</span>
                        )}
                        {exp.is_translated && (
                          <span className="translated-badge">Translated</span>
                        )}
                      </div>
                      <div className="card-footer">
                        <span className="file-size">{formatFileSize(exp.file_size)}</span>
                        <span className="file-date">
                          {exp.created_at ? new Date(exp.created_at).toLocaleDateString() : 'N/A'}
                        </span>
                      </div>
                    </div>
                    <div className="card-actions">
                      <button
                        className="view-btn"
                        onClick={() => handleView(exp)}
                      >
                        👁️ View
                      </button>
                      <button
                        className="download-btn"
                        onClick={() => handleDownload(exp, exp.file_path.split('/').pop())}
                      >
                        ⬇️ Download
                      </button>
                      <button
                        className="delete-btn"
                        onClick={(e) => handleDelete(exp, e)}
                        disabled={deletingId === (exp.id || exp.file_path)}
                        title="Delete file"
                      >
                        {deletingId === (exp.id || exp.file_path) ? '⏳' : '🗑️'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Documents Section */}
          {grouped.document.length > 0 && (currentFilter === 'all' || currentFilter === 'document') && (
            <div className="export-section">
              <h3>📄 Documents ({grouped.document.length})</h3>
              <div className="exports-grid">
                {grouped.document.map((exp) => (
                  <div key={exp.id || exp.file_path} className="export-card">
                    <div 
                      className="card-icon content-icon-clickable" 
                      onClick={() => handleView(exp)}
                      title="Click to view"
                    >
                      {getFileIcon(exp.file_type, exp.file_format)}
                    </div>
                    <div className="card-content">
                      <div className="card-title" title={exp.file_path.split('/').pop()}>
                        {getDisplayFileName(exp.file_path)}
                      </div>
                      <div className="card-meta">
                        <span className="format-badge">{exp.file_format.toUpperCase()}</span>
                        {exp.language && (
                          <span className="language-badge">{exp.language.toUpperCase()}</span>
                        )}
                        {exp.is_translated && (
                          <span className="translated-badge">Translated</span>
                        )}
                      </div>
                      <div className="card-footer">
                        <span className="file-size">{formatFileSize(exp.file_size)}</span>
                        <span className="file-date">
                          {exp.created_at ? new Date(exp.created_at).toLocaleDateString() : 'N/A'}
                        </span>
                      </div>
                    </div>
                    <div className="card-actions">
                      <button
                        className="view-btn"
                        onClick={() => handleView(exp)}
                      >
                        👁️ View
                      </button>
                      <button
                        className="download-btn"
                        onClick={() => handleDownload(exp, exp.file_path.split('/').pop())}
                      >
                        ⬇️ Download
                      </button>
                      <button
                        className="delete-btn"
                        onClick={(e) => handleDelete(exp, e)}
                        disabled={deletingId === (exp.id || exp.file_path)}
                        title="Delete file"
                      >
                        {deletingId === (exp.id || exp.file_path) ? '⏳' : '🗑️'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Audio Section */}
          {grouped.audio.length > 0 && (currentFilter === 'all' || currentFilter === 'audio') && (
            <div className="export-section">
              <h3>🔊 Audio ({grouped.audio.length})</h3>
              <div className="exports-grid">
                {grouped.audio.map((exp) => (
                  <div key={exp.id || exp.file_path} className="export-card">
                    <div 
                      className="card-icon audio-icon-clickable" 
                      onClick={() => handlePlayAudio(exp)}
                      title="Click to play"
                    >
                      {getFileIcon(exp.file_type, exp.file_format)}
                    </div>
                    <div className="card-content">
                      <div className="card-title" title={exp.file_path.split('/').pop()}>
                        {getDisplayFileName(exp.file_path)}
                      </div>
                      <div className="card-meta">
                        <span className="format-badge">{exp.file_format.toUpperCase()}</span>
                        {exp.language && (
                          <span className="language-badge">{exp.language.toUpperCase()}</span>
                        )}
                        {exp.is_translated && (
                          <span className="translated-badge">Translated</span>
                        )}
                      </div>
                      <div className="card-footer">
                        <span className="file-size">{formatFileSize(exp.file_size)}</span>
                        <span className="file-date">
                          {exp.created_at ? new Date(exp.created_at).toLocaleDateString() : 'N/A'}
                        </span>
                      </div>
                    </div>
                    <div className="card-actions">
                      <button
                        className="play-btn"
                        onClick={() => handlePlayAudio(exp)}
                      >
                        ▶️ Play
                      </button>
                      <button
                        className="download-btn"
                        onClick={() => handleDownload(exp, exp.file_path.split('/').pop())}
                      >
                        ⬇️ Download
                      </button>
                      <button
                        className="delete-btn"
                        onClick={(e) => handleDelete(exp, e)}
                        disabled={deletingId === (exp.id || exp.file_path)}
                        title="Delete file"
                      >
                        {deletingId === (exp.id || exp.file_path) ? '⏳' : '🗑️'}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Content Viewer Modal */}
      {viewingContent && viewingContent.type === 'content' && (
        <ContentViewer
          content={viewingContent.content}
          filename={viewingContent.filename}
          fileFormat={viewingContent.fileFormat}
          onClose={() => setViewingContent(null)}
        />
      )}

      {/* Audio Player Modal */}
      {viewingContent && viewingContent.type === 'audio' && (
        <AudioPlayer
          audioUrl={viewingContent.audioUrl}
          filename={viewingContent.filename}
          onClose={() => setViewingContent(null)}
        />
      )}
    </div>
  )
}

export default ExportsList