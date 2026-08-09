import { useTranslation } from 'react-i18next'

export function NotFoundRoute() {
  const { t } = useTranslation()

  return (
    <main>
      <h1>{t('notFound.title')}</h1>
    </main>
  )
}
