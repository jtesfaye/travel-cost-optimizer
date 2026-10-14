import { useEffect, useState } from 'react'
import './App.css'
import { RouterProvider } from 'react-router'
import { router } from './routes'
import { AppStateProvider } from './AppState'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

function App() {
  return (
    <AppStateProvider>
      <RouterProvider router={router} />
    </AppStateProvider>
  )
}

export default App
