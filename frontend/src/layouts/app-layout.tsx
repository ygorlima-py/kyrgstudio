import { Outlet } from 'react-router'

import { AppHeader } from '@/features/app-shell/components/app-header'
import { AppSidebar } from '@/features/app-shell/components/app-sidebar'

import { MobileNavigation } from '@/features/app-shell/components/mobile-navigation'
import { useTranslation } from 'react-i18next'

/**
 * Shared structure for every authenticated application page.
 */
export function AppLayout() {
  const { t } = useTranslation()
  return (
    <div className="min-h-svh bg-background text-text lg:flex">
      <a
        className="sr-only z-50 bg-surface px-4 py-3 text-label text-text focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
        href="#application-content"
      >
        {t('appLayout.skipToContent')}
      </a>

      <AppSidebar />

      <div className="min-w-0 flex-1">
        <AppHeader />

        <main
          className="mx-auto w-full max-w-[90rem] px-5 pb-24 pt-8 sm:px-7 lg:px-10 lg:py-10"
          id="application-content"
        >
          <Outlet />
        </main>

        <MobileNavigation />

      </div>
    </div>
  )
}