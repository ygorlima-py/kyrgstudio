import { useTranslation } from 'react-i18next'

import { RepeatableTextList } from './repeatable-text-list'

/**
 * Collects real evidence that the adaptation may use to support its claims.
 */
export function ProofAssetsFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="proof-assets-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="proof-assets-heading"
        >
          {t('userProfile.proofAssets.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.proofAssets.description')}
        </p>
      </div>

      <RepeatableTextList
        addLabel={t('userProfile.proofAssets.list.add')}
        description={t('userProfile.proofAssets.list.description')}
        itemLabel={t('userProfile.proofAssets.list.itemLabel')}
        label={t('userProfile.proofAssets.list.label')}
        name="user_profile.proof_assets"
      />
    </section>
  )
}
