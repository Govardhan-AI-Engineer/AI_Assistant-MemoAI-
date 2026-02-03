import React from 'react'
import './ContentViewer.css'

function ContentViewer({ content, filename, fileFormat, onClose }) {
  const renderContent = () => {
    if (!content) {
      return <div className="no-content">No content available</div>
    }

    // Format content based on file type
    if (fileFormat === 'json') {
      try {
        const jsonObj = JSON.parse(content)
        return (
          <pre className="content-json">
            {JSON.stringify(jsonObj, null, 2)}
          </pre>
        )
      } catch (e) {
        return <pre className="content-text">{content}</pre>
      }
    } else if (fileFormat === 'md') {
      // Simple markdown rendering (basic)
      return (
        <div className="content-markdown">
          {content.split('\n').map((line, idx) => {
            if (line.startsWith('# ')) {
              return <h1 key={idx}>{line.substring(2)}</h1>
            } else if (line.startsWith('## ')) {
              return <h2 key={idx}>{line.substring(3)}</h2>
            } else if (line.startsWith('### ')) {
              return <h3 key={idx}>{line.substring(4)}</h3>
            } else if (line.trim() === '') {
              return <br key={idx} />
            } else {
              return <p key={idx}>{line}</p>
            }
          })}
        </div>
      )
    } else {
      // Plain text, SRT, VTT
      return <pre className="content-text">{content}</pre>
    }
  }

  return (
    <div className="content-viewer-overlay" onClick={onClose}>
      <div className="content-viewer-modal" onClick={(e) => e.stopPropagation()}>
        <div className="content-viewer-header">
          <h3>{filename}</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>
        <div className="content-viewer-body">
          {renderContent()}
        </div>
        <div className="content-viewer-footer">
          <button className="close-btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}

export default ContentViewer
