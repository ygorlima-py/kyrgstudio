import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import en from './locales/en.json'
import ptBR from './locales/pt-BR.json'

const savedLanguage = localStorage.getItem('kyrg_language')

void i18n.use(initReactI18next).init({
  resources: {
    'pt-BR': {
      translation: ptBR,
    },
    en: {
      translation: en,
    },
  },
  lng: savedLanguage ?? 'pt-BR',
  fallbackLng: 'pt-BR',
  interpolation: {
    escapeValue: false,
  },
})

export { i18n }