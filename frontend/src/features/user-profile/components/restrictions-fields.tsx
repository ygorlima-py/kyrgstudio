import { useTranslation } from 'react-i18next'

import { RepeatableTextList } from './repeatable-text-list'

/**
 * Collects claims, topics, expressions, or promises that the adapted copy must
 * not use.
 */
export function RestrictionsFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="restrictions-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="restrictions-heading"
        >
          {t('userProfile.restrictions.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.restrictions.description')}
        </p>
      </div>

      <RepeatableTextList
        addLabel={t('userProfile.restrictions.list.add')}
        description={t('userProfile.restrictions.list.description')}
        itemLabel={t('userProfile.restrictions.list.itemLabel')}
        label={t('userProfile.restrictions.list.label')}
        name="user_profile.restrictions"
      />
    </section>
  )
}
