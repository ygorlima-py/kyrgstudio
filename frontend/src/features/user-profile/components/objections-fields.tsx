import { useTranslation } from 'react-i18next'

import { RepeatableTextList } from './repeatable-text-list'

/**
 * Collects the main reasons that may prevent the target audience from
 * accepting the offer.
 */
export function ObjectionsFields() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="objections-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="objections-heading"
        >
          {t('userProfile.objections.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.objections.description')}
        </p>
      </div>

      <RepeatableTextList
        addLabel={t('userProfile.objections.list.add')}
        description={t('userProfile.objections.list.description')}
        itemLabel={t('userProfile.objections.list.itemLabel')}
        label={t('userProfile.objections.list.label')}
        name="user_profile.objections"
      />
    </section>
  )
}
