import { useTranslation } from 'react-i18next'

import { ProfileTextField } from './profile-text-field'

/**
 * Defines the audience's desired outcome and the responsible promise the
 * adapted copy may communicate.
 */
export function DesirePromiseFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="desire-promise-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="desire-promise-heading"
        >
          {t('userProfile.desirePromise.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.desirePromise.description')}
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ProfileTextField
          description={t('userProfile.desirePromise.desire.description')}
          label={t('userProfile.desirePromise.desire.label')}
          name="user_profile.core_desire"
          placeholder={t('userProfile.desirePromise.desire.placeholder')}
        />

        <ProfileTextField
          description={t('userProfile.desirePromise.promise.description')}
          label={t('userProfile.desirePromise.promise.label')}
          name="user_profile.main_promise"
          placeholder={t('userProfile.desirePromise.promise.placeholder')}
        />
      </div>
    </section>
  )
}
