import { useTranslation } from 'react-i18next'

import { ProfileTextField } from './profile-text-field'

/**
 * Collects the commercial conditions that may be communicated in the adapted
 * copy.
 */
export function OfferTermsFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="offer-details-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="offer-details-heading"
        >
          {t('userProfile.offerTerms.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.offerTerms.description')}
        </p>
      </div>

      <ProfileTextField
        description={t('userProfile.offerTerms.field.description')}
        label={t('userProfile.offerTerms.field.label')}
        name="user_profile.offer_details"
        placeholder={t('userProfile.offerTerms.field.placeholder')}
      />
    </section>
  )
}
