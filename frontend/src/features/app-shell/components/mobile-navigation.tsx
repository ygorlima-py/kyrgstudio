import { useTranslation } from 'react-i18next'
import { NavLink } from 'react-router'

import { cn } from '@/shared/utils/class-names'

import { APP_NAVIGATION_ITEMS } from '../config/navigation-items'

/**
 * Bottom navigation for authenticated pages on smaller screens.
 */
export function MobileNavigation() {
  const { t } = useTranslation()

  return (
    <nav
      aria-label={t('appNavigation.mobileAriaLabel')}
      className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-surface/95 pb-[env(safe-area-inset-bottom)] backdrop-blur lg:hidden"
    >
      <ul
        className="grid"
        style={{
          gridTemplateColumns: `repeat(${APP_NAVIGATION_ITEMS.length}, minmax(0, 1fr))`,
        }}
      >
        {APP_NAVIGATION_ITEMS.map((item) => (
          <li key={item.path}>
            <NavLink
              className={({ isActive }) =>
                cn(
                  'relative flex min-h-16 items-center justify-center px-3',
                  'text-body-sm font-medium text-text-muted',
                  'transition-colors hover:text-text',
                  isActive &&
                    'text-action after:absolute after:inset-x-6 after:top-0 after:h-0.5 after:bg-action',
                )
              }
              end={item.exact}
              to={item.path}
            >
              {t(item.labelKey)}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}