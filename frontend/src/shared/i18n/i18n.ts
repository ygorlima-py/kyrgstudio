import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import ptBR from './locales/pt-BR.json'

export const DEFAULT_LANGUAGE = 'pt-BR'
export const LANGUAGE_STORAGE_KEY = 'kyrg_language'

export type SupportedLanguage = 'pt-BR' | 'en'

function getLanguageFromPath(pathname: string): SupportedLanguage | null {
  if (pathname === '/en' || pathname.startsWith('/en/')) {
    return 'en'
  }

  if (pathname === '/pt-BR' || pathname.startsWith('/pt-BR/')) {
    return 'pt-BR'
  }

  return null
}

const routeLanguage =
  typeof window !== 'undefined' ? getLanguageFromPath(window.location.pathname) : null

const hasPrerenderedLanding =
  typeof window !== 'undefined' &&
  (window.location.pathname === '/' || routeLanguage !== null) &&
  document.getElementById('root')?.hasChildNodes() === true

const savedLanguage =
  typeof localStorage !== 'undefined' && !hasPrerenderedLanding
    ? localStorage.getItem(LANGUAGE_STORAGE_KEY)
    : null

void i18n.use(initReactI18next).init({
  resources: {
    'pt-BR': {
      translation: ptBR,
    },
    en: {
      translation: en,
    },
  },
  lng: routeLanguage ?? savedLanguage ?? DEFAULT_LANGUAGE,
  fallbackLng: DEFAULT_LANGUAGE,
  interpolation: {
    escapeValue: false,
  },
})

export { getLanguageFromPath, i18n }
