import { useTranslation } from 'react-i18next'

import { RepeatableTextList } from './repeatable-text-list'

/**
 * Collects the concrete benefits that the adapted copy may communicate.
 */
export function BenefitsFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="benefits-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="benefits-heading"
        >
          {t('userProfile.benefits.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.benefits.description')}
        </p>
      </div>

      <RepeatableTextList
        addLabel={t('userProfile.benefits.list.add')}
        description={t('userProfile.benefits.list.description')}
        itemLabel={t('userProfile.benefits.list.itemLabel')}
        label={t('userProfile.benefits.list.label')}
        name="user_profile.benefits"
      />
    </section>
  )
}
