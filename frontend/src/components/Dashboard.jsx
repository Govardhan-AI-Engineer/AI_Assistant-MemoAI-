import React, { useState } from 'react'
import TranscriptionPanel from './TranscriptionPanel'
import TranslationPanel from './TranslationPanel'
import TranscriptsList from './TranscriptsList'
import ExportsList from './ExportsList'
import RAGPanel from './RAGPanel'
import './Dashboard.css'

function Dashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('transcribe')
  const [currentTranscript, setCurrentTranscript] = useState(null)

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div className="header-content">
          <h1>🎤 MemoAI</h1>
          <div className="header-right">
            <span className="user-info">👤 {user.user?.username || 'User'}</span>
            <button onClick={onLogout} className="logout-btn">Logout</button>
          </div>
        </div>
      </header>

      <div className="dashboard-content">
        <nav className="tabs">
          <button
            className={activeTab === 'transcribe' ? 'active' : ''}
            onClick={() => setActiveTab('transcribe')}
          >
            📝 Transcribe
          </button>
          <button
            className={activeTab === 'transcripts' ? 'active' : ''}
            onClick={() => setActiveTab('transcripts')}
          >
            📚 My Transcripts
          </button>
          <button
            className={activeTab === 'exports' ? 'active' : ''}
            onClick={() => setActiveTab('exports')}
          >
            📦 My Exports
          </button>
          <button
            className={activeTab === 'rag' ? 'active' : ''}
            onClick={() => setActiveTab('rag')}
          >
            🤖 Ask Questions
          </button>
        </nav>

        <div className="tab-content">
          {activeTab === 'transcribe' && (
            <div className="transcribe-section">
              <TranscriptionPanel
                user={user}
                onTranscriptionComplete={(transcript) => {
                  setCurrentTranscript(transcript)
                  // Keep on transcribe tab to show translation panel
                }}
              />
              {currentTranscript && (
                <div style={{ marginTop: '2rem' }}>
                  <TranslationPanel
                    user={user}
                    transcript={currentTranscript}
                  />
                </div>
              )}
            </div>
          )}

          {activeTab === 'transcripts' && (
            <div>
              <TranscriptsList
                user={user}
                onSelectTranscript={(transcript) => {
                  setCurrentTranscript(transcript)
                  setActiveTab('transcribe') // Switch to transcribe tab to show translation panel
                }}
              />
            </div>
          )}

          {activeTab === 'exports' && (
            <ExportsList user={user} />
          )}

          {activeTab === 'rag' && (
            <RAGPanel user={user} />
          )}
        </div>
      </div>
    </div>
  )
}

export default Dashboard
