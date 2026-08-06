import { Link } from 'react-router'

import { useAuth } from '@/features/auth'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu'

import { LanguageSwitcher } from '@/shared/components/language-switcher'

import { useTranslation } from 'react-i18next'

/**
 * Application header containing mobile branding and the authenticated user menu.
 */
export function AppHeader() {
  const { t } = useTranslation()
  const session = useAuth()

  if (session.status !== 'authenticated') {
    return null
  }

  const displayName = session.user.name?.trim() || session.user.email
  const userInitial = displayName.charAt(0).toUpperCase()

  function handleLogout(): void {
    void session.logout().catch(() => undefined)
  }

  return (
    <header className="sticky top-0 z-30 flex h-20 items-center justify-between border-b border-border bg-background/95 px-5 backdrop-blur sm:px-7 lg:justify-end lg:px-10">
      <Link
        className="font-heading text-xl font-semibold tracking-tight text-text lg:hidden"
        to="/app"
      >
        Kyrg Studio
      </Link>

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            aria-label={t('appHeader.openUserMenu')}
            className="flex items-center gap-3 rounded-md text-left focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus"
            type="button"
          >
            <span className="hidden max-w-48 truncate text-body-sm font-medium text-text sm:block">
              {displayName}
            </span>

            <span
              aria-hidden="true"
              className="flex size-10 items-center justify-center rounded-full border border-border-strong font-heading text-lg font-semibold text-action"
            >
              {userInitial}
            </span>
          </button>
        </DropdownMenuTrigger>

        <DropdownMenuContent align="end" className="w-64">
          <DropdownMenuLabel>
            <span className="block truncate text-text">{displayName}</span>
            <span className="mt-0.5 block truncate text-body-sm font-normal text-text-muted">
              {session.user.email}
            </span>
          </DropdownMenuLabel>

          <DropdownMenuSeparator />

          <div className="px-3 py-3">
            <LanguageSwitcher />
          </div>

          <DropdownMenuSeparator />

          <DropdownMenuItem onSelect={handleLogout}>
            {t('appHeader.logout')}
          </DropdownMenuItem>
          
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}