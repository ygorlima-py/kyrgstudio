import { useTranslation } from 'react-i18next'

import { ProfileTextField } from './profile-text-field'

/**
 * Defines the action the audience should take after consuming the adapted
 * sales message.
 */
export function CallToActionFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="call-to-action-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="call-to-action-heading"
        >
          {t('userProfile.callToAction.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.callToAction.description')}
        </p>
      </div>

      <ProfileTextField
        description={t('userProfile.callToAction.field.description')}
        label={t('userProfile.callToAction.field.label')}
        name="user_profile.call_to_action"
        placeholder={t('userProfile.callToAction.field.placeholder')}
      />
    </section>
  )
}
