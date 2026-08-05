import { useTranslation } from 'react-i18next'
import { Link, Outlet } from 'react-router'

import { LanguageSwitcher } from '@/shared/components/language-switcher'

/**
 * Provides a minimal shared structure for authentication pages.
 */
export function AuthLayout() {
  const { t } = useTranslation()

  return (
    <div className="min-h-svh bg-background text-text">
      <header className="mx-auto flex h-20 max-w-7xl items-center justify-between px-6 lg:px-10">
        <Link
          className="font-heading text-2xl font-semibold tracking-tight text-text"
          to="/"
        >
          Kyrg Studio
        </Link>

        <div className="flex items-center gap-5">
          <LanguageSwitcher />

          <Link
            className="text-label text-text-muted transition-colors hover:text-text"
            to="/"
          >
            {t('auth.layout.backHome')}
          </Link>
        </div>
      </header>

      <main className="flex min-h-[calc(100svh-5rem)] justify-center px-6 py-12 sm:px-10 sm:py-16">
        <div className="w-full max-w-md">
          <Outlet />
        </div>
      </main>
    </div>
  )
}