import React, { useState } from 'react'
import axios from 'axios'
import './Login.css'

const API_URL = 'http://localhost:8000'

function Login({ onLogin }) {
  const [mode, setMode] = useState('login') // 'login' or 'register'
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      if (mode === 'register') {
        const response = await axios.post(`${API_URL}/api/auth/register`, {
          username,
          password
        })
        if (response.data.success) {
          // Auto-login after registration
          const loginResponse = await axios.post(`${API_URL}/api/auth/login`, {
            username,
            password
          })
          if (loginResponse.data.success) {
            onLogin(loginResponse.data)
          }
        }
      } else {
        const response = await axios.post(`${API_URL}/api/auth/login`, {
          username,
          password
        })
        if (response.data.success) {
          onLogin(response.data)
        } else {
          setError('Login failed')
        }
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'An error occurred')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-box">
        <h1>MemoAI</h1>
        <p className="subtitle">Transcription & Translation Assistant</p>

        <div className="mode-toggle">
          <button
            className={mode === 'login' ? 'active' : ''}
            onClick={() => setMode('login')}
          >
            Login
          </button>
          <button
            className={mode === 'register' ? 'active' : ''}
            onClick={() => setMode('register')}
          >
            Register
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loading}
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              disabled={loading}
            />
          </div>

          {error && <div className="error">{error}</div>}

          <button type="submit" disabled={loading} className="submit-btn">
            {loading ? 'Processing...' : mode === 'login' ? 'Login' : 'Register'}
          </button>
        </form>
      </div>
    </div>
  )
}

export default Login
