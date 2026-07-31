import { Link, NavLink } from 'react-router'

import { cn } from '@/shared/utils/class-names'

import { APP_NAVIGATION_ITEMS } from '../config/navigation-items'

/**
 * Desktop navigation for authenticated application pages.
 */
export function AppSidebar() {
  return (
    <aside className="sticky top-0 hidden h-svh w-68 shrink-0 flex-col border-r border-border bg-surface lg:flex">
      <div className="flex h-20 items-center border-b border-border px-6">
        <Link
          className="font-heading text-2xl font-semibold tracking-tight text-text"
          to="/app"
        >
          Kyrg Studio
        </Link>
      </div>

      <nav
        aria-label="Application navigation"
        className="flex-1 px-4 py-7"
      >
        <ul className="space-y-1">
          {APP_NAVIGATION_ITEMS.map((item) => (
            <li key={item.path}>
              <NavLink
                className={({ isActive }) =>
                  cn(
                    'relative flex min-h-11 items-center px-4 text-body-sm font-medium',
                    'text-text-muted transition-colors hover:text-text',
                    isActive &&
                      'text-action before:absolute before:inset-y-2 before:left-0 before:w-0.5 before:bg-action',
                  )
                }
                end={item.exact}
                to={item.path}
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-border px-6 py-5">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-text-subtle">
          Analysis workspace
        </p>
      </div>
    </aside>
  )
}