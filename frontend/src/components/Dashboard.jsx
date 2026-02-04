import React, { useState } from 'react'
import TranscriptionPanel from './TranscriptionPanel'
import TranslationPanel from './TranslationPanel'
import TranscriptsList from './TranscriptsList'
import ExportsList from './ExportsList'
import RAGPanel from './RAGPanel'
import NotesPanel from './NotesPanel'
import TagsPanel from './TagsPanel'
import ExportButton from './ExportButton'
import './Dashboard.css'

function Dashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('transcribe')
  const [currentTranscript, setCurrentTranscript] = useState(null)
  const [selectedTranscript, setSelectedTranscript] = useState(null)
  const [transcriptView, setTranscriptView] = useState('all') // 'all', 'search', 'filter'
  const [exportFilter, setExportFilter] = useState('all') // 'all', 'subtitle', 'document', 'audio'
  const [activeSubTab, setActiveSubTab] = useState('transcription') // 'transcription', 'translation', 'notes', 'tags'

  return (
    <div className="dashboard">
      {/* Top Header Bar */}
      <header className="top-header">
        <div className="header-left">
          <div className="logo">
            <img src="/Logo.png" alt="MemoAI Logo" className="logo-image" />
            <div className="logo-tagline">Transcribe • Translate • Organize</div>
          </div>
        </div>
        <div className="header-center">
          <nav className="main-nav-tabs">
            <button
              className={`nav-tab ${activeTab === 'transcribe' ? 'active' : ''}`}
              onClick={() => setActiveTab('transcribe')}
            >
              Transcribe
            </button>
            <button
              className={`nav-tab ${activeTab === 'transcripts' ? 'active' : ''}`}
              onClick={() => setActiveTab('transcripts')}
            >
              Transcripts
            </button>
            <button
              className={`nav-tab ${activeTab === 'exports' ? 'active' : ''}`}
              onClick={() => setActiveTab('exports')}
            >
              Exports
            </button>
            <button
              className={`nav-tab ${activeTab === 'rag' ? 'active' : ''}`}
              onClick={() => setActiveTab('rag')}
            >
              Ask Questions
            </button>
          </nav>
        </div>
        <div className="header-right">
          <div className="notification-icon">🔔</div>
          <div className="user-profile">
            <div className="user-avatar">
              {user.user?.username?.charAt(0).toUpperCase() || 'U'}
            </div>
            <div className="user-details">
              <div className="user-name">{user.user?.username || 'User'}</div>
              <div className="user-email">{user.user?.email || 'user@example.com'}</div>
            </div>
          </div>
          <button onClick={onLogout} className="logout-btn">Logout</button>
        </div>
      </header>

      <div className="dashboard-layout">
        {/* Left Sidebar */}
        <aside className="sidebar">
          <div className="sidebar-section">
            <div className="project-selector">
              <span className="project-icon">🎤</span>
              <span className="project-name"> MemoAI</span>
              <span className="dropdown-arrow">▼</span>
            </div>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-title">Overview</div>
            <div className={`sidebar-item ${activeTab === 'transcribe' ? 'active' : ''}`}
                 onClick={() => setActiveTab('transcribe')}>
              <span className="sidebar-icon">📝</span>
              <span>Transcribe</span>
            </div>
          </div>

          <div className="sidebar-section">
            <div className="sidebar-title">Features</div>
            <div className={`sidebar-item ${activeTab === 'transcripts' ? 'active' : ''}`}
                 onClick={() => setActiveTab('transcripts')}>
              <span className="sidebar-icon">📚</span>
              <span>My Transcripts</span>
            </div>
            <div className={`sidebar-item ${activeTab === 'exports' ? 'active' : ''}`}
                 onClick={() => setActiveTab('exports')}>
              <span className="sidebar-icon">📦</span>
              <span>My Exports</span>
            </div>
            <div className={`sidebar-item ${activeTab === 'rag' ? 'active' : ''}`}
                 onClick={() => setActiveTab('rag')}>
              <span className="sidebar-icon">🤖</span>
              <span>Ask Questions</span>
            </div>
          </div>

          <div className="sidebar-section">
            <div 
              className={`sidebar-item ${activeTab === 'transcribe' && (activeSubTab === 'notes' || activeSubTab === 'tags') ? 'active' : ''}`}
              onClick={() => {
                setActiveTab('transcribe')
                // Always route to notes tab - NotesPanel has its own transcript selector
                setActiveSubTab('notes')
                // Preserve currentTranscript if it exists, but NotesPanel can work without it
                // NotesPanel will show transcript selector if no transcript is selected
              }}
            >
              <span className="sidebar-icon">📋</span>
              <span>Notes & Tags</span>
            </div>
            <div className="sidebar-item">
              <span className="sidebar-icon">⚙️</span>
              <span>Settings</span>
            </div>
          </div>
        </aside>

        {/* Main Content Area */}
        <main className="main-content">
          {/* Sub-navigation for current tab */}
          <div className="sub-nav">
            {activeTab === 'transcribe' && (
              <>
                <button 
                  className={`sub-nav-tab ${activeSubTab === 'transcription' ? 'active' : ''}`}
                  onClick={() => setActiveSubTab('transcription')}
                >
                  Transcription
                </button>
                {currentTranscript && (
                  <button 
                    className={`sub-nav-tab ${activeSubTab === 'translation' ? 'active' : ''}`}
                    onClick={() => setActiveSubTab('translation')}
                  >
                    Translation
                  </button>
                )}
                <button 
                  className={`sub-nav-tab ${activeSubTab === 'notes' ? 'active' : ''}`}
                  onClick={() => setActiveSubTab('notes')}
                >
                  Notes
                </button>
                <button 
                  className={`sub-nav-tab ${activeSubTab === 'tags' ? 'active' : ''}`}
                  onClick={() => setActiveSubTab('tags')}
                >
                  Tags
                </button>
              </>
            )}
            {activeTab === 'transcripts' && (
              <>
                <button 
                  className={`sub-nav-tab ${transcriptView === 'all' ? 'active' : ''}`}
                  onClick={() => setTranscriptView('all')}
                >
                  All Transcripts
                </button>
                <button 
                  className={`sub-nav-tab ${transcriptView === 'search' ? 'active' : ''}`}
                  onClick={() => setTranscriptView('search')}
                >
                  Search
                </button>
                <button 
                  className={`sub-nav-tab ${transcriptView === 'filter' ? 'active' : ''}`}
                  onClick={() => setTranscriptView('filter')}
                >
                  Filter
                </button>
              </>
            )}
            {activeTab === 'exports' && (
              <>
                <button 
                  className={`sub-nav-tab ${exportFilter === 'all' ? 'active' : ''}`}
                  onClick={() => setExportFilter('all')}
                >
                  All Exports
                </button>
                <button 
                  className={`sub-nav-tab ${exportFilter === 'subtitle' ? 'active' : ''}`}
                  onClick={() => setExportFilter('subtitle')}
                >
                  Subtitles
                </button>
                <button 
                  className={`sub-nav-tab ${exportFilter === 'document' ? 'active' : ''}`}
                  onClick={() => setExportFilter('document')}
                >
                  Documents
                </button>
                <button 
                  className={`sub-nav-tab ${exportFilter === 'audio' ? 'active' : ''}`}
                  onClick={() => setExportFilter('audio')}
                >
                  Audio
                </button>
              </>
            )}
            {activeTab === 'rag' && (
              <>
                <button className="sub-nav-tab active">Query</button>
                <button className="sub-nav-tab">Indexing</button>
                <button className="sub-nav-tab">Stats</button>
              </>
            )}
          </div>

          {/* Content Panels */}
          <div className="content-panels">
            {activeTab === 'transcribe' && (
              <div className="single-panel">
                {activeSubTab === 'transcription' && (
                  <TranscriptionPanel
                    user={user}
                    onTranscriptionComplete={(transcript) => {
                      setCurrentTranscript(transcript)
                      setActiveSubTab('translation') // Switch to translation tab after transcription
                    }}
                  />
                )}
                {activeSubTab === 'translation' && currentTranscript && (
                  <TranslationPanel
                    user={user}
                    transcript={currentTranscript}
                    onLanguageChange={(lang) => {
                      // Update currentTranscript with selected language for NotesPanel and ExportButton
                      setCurrentTranscript({ ...currentTranscript, selectedLanguage: lang, targetLanguage: lang })
                    }}
                    onNavigateToNotes={(targetLang) => {
                      // Update transcript with target language and switch to notes tab
                      setCurrentTranscript({ 
                        ...currentTranscript, 
                        selectedLanguage: targetLang, 
                        targetLanguage: targetLang 
                      })
                      setActiveSubTab('notes')
                    }}
                  />
                )}
                {activeSubTab === 'notes' && (
                  <NotesPanel
                    user={user}
                    transcriptId={currentTranscript?.id || currentTranscript?.transcript_id || null}
                    targetLanguage={currentTranscript?.selectedLanguage || null}
                    onTranscriptSelect={(transcript) => {
                      setCurrentTranscript(transcript)
                    }}
                  />
                )}
                {activeSubTab === 'tags' && (
                  <TagsPanel
                    user={user}
                    transcriptId={currentTranscript?.id || currentTranscript?.transcript_id || null}
                    onTagsUpdate={() => {}}
                    onTranscriptSelect={(transcript) => {
                      setCurrentTranscript(transcript)
                    }}
                  />
                )}
                {!currentTranscript && activeSubTab === 'translation' && (
                  <div style={{ padding: '2rem', textAlign: 'center', color: '#666' }}>
                    <p>Please transcribe a file first to access translation features.</p>
                    <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginTop: '1rem' }}>
                      <button 
                        onClick={() => setActiveSubTab('transcription')}
                        style={{
                          padding: '0.5rem 1rem',
                          background: '#285d93',
                          color: 'white',
                          border: 'none',
                          borderRadius: '4px',
                          cursor: 'pointer',
                          fontFamily: 'Helvetica, Arial, sans-serif'
                        }}
                      >
                        Go to Transcription
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'transcripts' && (
              <div className="two-panel-layout">
                <div className="left-panel">
                  <TranscriptsList
                    user={user}
                    activeView={transcriptView}
                    onSelectTranscript={(transcript) => {
                      setSelectedTranscript(transcript)
                      setCurrentTranscript(transcript)
                    }}
                  />
                </div>
                {selectedTranscript && (
                  <div className="right-panel">
                    <div className="panel-header">
                      <h3>Transcript Details</h3>
                      <span className="created-date">
                        Created on {new Date(selectedTranscript.created_at).toLocaleDateString()}
                      </span>
                    </div>
                    <div className="panel-content">
                      <div className="detail-section">
                        <h4>{selectedTranscript.source_file || selectedTranscript.source_url || 'Untitled'}</h4>
                        <div className="meta-badges">
                          <span className="badge">{selectedTranscript.language}</span>
                          <span className="badge">{selectedTranscript.model_used || 'Unknown'}</span>
                        </div>
                      </div>
                      <div className="detail-section">
                        <h5>Content</h5>
                        <p className="transcript-text">{selectedTranscript.text}</p>
                      </div>
                      {selectedTranscript.tags && selectedTranscript.tags.length > 0 && (
                        <div className="detail-section">
                          <h5>Tags</h5>
                          <div className="tags-list">
                            {selectedTranscript.tags.map((tag) => (
                              <span key={tag.id} className="tag-badge" style={{ backgroundColor: tag.color || '#e0e0e0' }}>
                                {tag.name}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      <div className="panel-actions">
                        <button
                          className="action-btn primary"
                          onClick={() => {
                            setCurrentTranscript(selectedTranscript)
                            setActiveTab('transcribe')
                          }}
                        >
                          Translate
                        </button>
                        <button 
                          className="action-btn"
                          onClick={() => {
                            setCurrentTranscript(selectedTranscript)
                            setActiveTab('transcribe')
                            setActiveSubTab('notes')
                          }}
                        >
                          View Notes
                        </button>
                      </div>
                      <div className="export-actions">
                        <h5>Export Options</h5>
                        <div className="export-buttons">
                          <ExportButton
                            user={user}
                            transcriptId={selectedTranscript.id}
                            type="subtitle"
                            icon="📄"
                            label="Subtitles"
                            formats={['srt', 'vtt', 'both']}
                          />
                          <ExportButton
                            user={user}
                            transcriptId={selectedTranscript.id}
                            type="document"
                            icon="📝"
                            label="Documents"
                            formats={['md', 'txt', 'json']}
                          />
                          <ExportButton
                            user={user}
                            transcriptId={selectedTranscript.id}
                            type="audio"
                            icon="🔊"
                            label="Audio"
                            formats={['mp3', 'wav']}
                            targetLanguage={selectedTranscript.targetLanguage || currentTranscript?.targetLanguage || null}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'exports' && (
              <div className="single-panel">
                <ExportsList user={user} filterType={exportFilter} />
              </div>
            )}

            {activeTab === 'rag' && (
              <div className="single-panel">
                <RAGPanel user={user} />
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  )
}

export default Dashboard
