import { useEffect, useState } from 'react'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function App() {
  const [apiStatus, setApiStatus] = useState('checking...')

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/health`)
      .then((res) => res.json())
      .then((data) => setApiStatus(data.status))
      .catch(() => setApiStatus('unreachable'))
  }, [])

  return (
    <div className="app">
      <h1>Travel Cost Optimizer</h1>
      <p>
        Backend status: <strong>{apiStatus}</strong>
      </p>
    </div>
  )
}

export default App
