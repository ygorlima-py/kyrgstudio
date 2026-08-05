import { useEffect, type ComponentProps } from 'react'
import { RouterProvider } from 'react-router/dom'
import { getLanguageFromPath, i18n, LANGUAGE_STORAGE_KEY } from '@/shared/i18n/i18n'

import { AppProviders } from '@/app/providers'

interface AppProps {
  readonly applicationRouter: ComponentProps<typeof RouterProvider>['router']
}

export function App({ applicationRouter }: AppProps) {
  useEffect(() => {
    const routeLanguage = getLanguageFromPath(window.location.pathname)
    const savedLanguage = localStorage.getItem(LANGUAGE_STORAGE_KEY)
    const resolvedLanguage = routeLanguage ?? savedLanguage

    if (resolvedLanguage && resolvedLanguage !== i18n.resolvedLanguage) {
      void i18n.changeLanguage(resolvedLanguage)
    }

    if (resolvedLanguage) {
      document.documentElement.setAttribute('lang', resolvedLanguage)
    }
  }, [])

  return (
    <AppProviders>
      <RouterProvider router={applicationRouter} />
    </AppProviders>
  )
}
