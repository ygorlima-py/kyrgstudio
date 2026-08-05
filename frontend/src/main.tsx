import '@/shared/i18n/i18n'

import { getLanguageFromPath } from '@/shared/i18n/i18n'

import { StrictMode } from 'react'
import { createRoot, hydrateRoot } from 'react-dom/client'

import '@fontsource-variable/fraunces/opsz.css'
import '@fontsource-variable/instrument-sans/wght.css'
import '@fontsource/ibm-plex-mono/latin-400.css'
import '@fontsource/ibm-plex-mono/latin-500.css'

import '@fortawesome/fontawesome-free/css/all.min.css'

import '@/styles/globals.css'
import { App } from '@/app/app'
import { router } from '@/app/router'
const rootElement = document.getElementById('root')

if (!rootElement) {
  throw new Error('Application root element was not found')
}

const application = (
  <StrictMode>
    <App applicationRouter={router} />
  </StrictMode>
)

const shouldHydrateLanding =
  rootElement.hasChildNodes() &&
  (window.location.pathname === '/' || getLanguageFromPath(window.location.pathname) !== null)

if (shouldHydrateLanding) {
  hydrateRoot(rootElement, application)
} else {
  // Vite preview may return the landing document as a fallback for client routes.
  rootElement.replaceChildren()
  createRoot(rootElement).render(application)
}
