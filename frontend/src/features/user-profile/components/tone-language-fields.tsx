import { useTranslation } from 'react-i18next'

import { ProfileTextField } from './profile-text-field'

/**
 * Defines how the adapted copy should sound and which language it should use
 * in the final script.
 */
export function ToneLanguageFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="tone-language-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="tone-language-heading"
        >
          {t('userProfile.toneLanguage.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.toneLanguage.description')}
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ProfileTextField
          description={t('userProfile.toneLanguage.tone.description')}
          label={t('userProfile.toneLanguage.tone.label')}
          name="user_profile.tone"
          placeholder={t('userProfile.toneLanguage.tone.placeholder')}
        />

        <ProfileTextField
          description={t('userProfile.toneLanguage.language.description')}
          label={t('userProfile.toneLanguage.language.label')}
          multiline={false}
          name="user_profile.target_language"
          placeholder={t('userProfile.toneLanguage.language.placeholder')}
        />
      </div>
    </section>
  )
}
