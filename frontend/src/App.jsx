import { useEffect, useState } from 'react'
import './App.css'
import { RouterProvider } from 'react-router'
import { router } from './routes'
import { APIProvider } from '@vis.gl/react-google-maps'
import { AppStateProvider } from './AppState'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const MAPS_API_KEY = import.meta.env.VITE_GOOGLE_MAPS_API_KEY ?? ''

function App() {
  return (
    <APIProvider apiKey={MAPS_API_KEY}>
      <AppStateProvider>
        <RouterProvider router={router} />
      </AppStateProvider>
    </APIProvider>
  )
}

export default App
