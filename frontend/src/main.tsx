import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import '@fontsource-variable/fraunces/opsz.css'
import '@fontsource-variable/instrument-sans/wght.css'
import '@fontsource/ibm-plex-mono/latin-400.css'
import '@fontsource/ibm-plex-mono/latin-500.css'

import '@/styles/globals.css'
import { App } from '@/app/app'
const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('Application root element was not found')
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
