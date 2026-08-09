import { useTranslation } from 'react-i18next'

/**
 * Explains why the user was redirected to the login page.
 */
export function SessionExpired() {
  const { t } = useTranslation()

  return (
    <div className="border-l-2 border-warning pl-4" role="status">
      <p className="text-label text-text">{t('auth.session.expiredTitle')}</p>
      <p className="mt-1 text-body-sm text-text-muted">
        {t('auth.session.expiredDescription')}
      </p>
    </div>
  )
}
