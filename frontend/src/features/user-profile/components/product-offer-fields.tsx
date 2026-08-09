import { useTranslation } from 'react-i18next'

import { ProfileTextField } from './profile-text-field'

/**
 * Collects the basic description of the product, service, or solution that
 * will replace the original offer during copy adaptation.
 */
export function ProductOfferFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="product-offer-heading"
      className="space-y-5"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="product-offer-heading"
        >
          {t('userProfile.productOffer.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.productOffer.description')}
        </p>
      </div>

      <ProfileTextField
        description={t('userProfile.productOffer.product.description')}
        label={t('userProfile.productOffer.product.label')}
        name="user_profile.product_or_solution"
        placeholder={t('userProfile.productOffer.product.placeholder')}
      />
    </section>
  )
}
