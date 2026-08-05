import { faGlobe } from '@fortawesome/free-solid-svg-icons'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { useTranslation } from 'react-i18next'

import { cn } from '@/shared/utils/class-names'

const LANGUAGE_OPTIONS = [
  {
    value: 'pt-BR',
    shortLabel: 'PT',
    accessibleLabel: 'Português',
  },
  {
    value: 'en',
    shortLabel: 'EN',
    accessibleLabel: 'English',
  },
] as const

type SupportedLanguage = (typeof LANGUAGE_OPTIONS)[number]['value']

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation()

  const currentLanguage: SupportedLanguage =
    i18n.resolvedLanguage?.startsWith('en') === true ? 'en' : 'pt-BR'

  async function selectLanguage(language: SupportedLanguage) {
    if (language === currentLanguage) {
      return
    }

    await i18n.changeLanguage(language)

    localStorage.setItem('kyrg_language', language)
    document.documentElement.lang = language
  }

  return (
    <div
      aria-label={t('language.selector')}
      className="inline-flex items-center gap-2"
      role="group"
    >
      <FontAwesomeIcon
        aria-hidden="true"
        className="text-text-muted"
        icon={faGlobe}
      />

      <div className="inline-flex rounded-pill border border-border bg-surface p-1">
        {LANGUAGE_OPTIONS.map((language) => {
          const isSelected = language.value === currentLanguage

          return (
            <button
              aria-label={language.accessibleLabel}
              aria-pressed={isSelected}
              className={cn(
                'rounded-pill px-2.5 py-1 text-xs font-semibold transition-colors',
                isSelected
                  ? 'bg-action text-text-inverse'
                  : 'text-text-muted hover:text-text',
              )}
              key={language.value}
              onClick={() => {
                void selectLanguage(language.value)
              }}
              type="button"
            >
              {language.shortLabel}
            </button>
          )
        })}
      </div>
    </div>
  )
}