import { useTranslation } from 'react-i18next'

import { ProfileTextField } from './profile-text-field'

/**
 * Describes the method or approach that explains how the offer produces its
 * intended result.
 */
export function MechanismFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="mechanism-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="mechanism-heading"
        >
          {t('userProfile.mechanism.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.mechanism.description')}
        </p>
      </div>

      <ProfileTextField
        description={t('userProfile.mechanism.field.description')}
        label={t('userProfile.mechanism.field.label')}
        name="user_profile.unique_mechanism"
        placeholder={t('userProfile.mechanism.field.placeholder')}
      />
    </section>
  )
}
