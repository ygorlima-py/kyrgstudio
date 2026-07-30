import { Outlet } from 'react-router'

import { MarketingHeader } from '@/features/marketing/components/marketing-header'
import { MarketingFooter } from '@/features/marketing/components/marketing-footer'

/**
 * Shared shell for public marketing pages.
 *
 * The layout owns the page-level background and primary content landmark.
 * Marketing pages are rendered through Outlet and remain responsible for
 * their own sections and content width.
 */
export function MarketingLayout() {
  return (
    <div className="min-h-dvh overflow-x-clip bg-background text-text">
      <MarketingHeader />
        <a
            className={[
            'fixed top-3 left-3 z-50 -translate-y-20 rounded-md',
            'bg-text px-4 py-2 text-label text-text-inverse shadow-md',
            'transition-transform duration-(--duration-fast) ease-standard',
            'focus:translate-y-0 focus:outline-none focus:ring-3 focus:ring-focus',
            'focus:ring-offset-2 focus:ring-offset-background',
            ].join(' ')}
            href="#main-content"
        >
            Skip to content
        </a>

        <main className="min-h-dvh outline-none" id="main-content" tabIndex={-1}>
            <Outlet />
        </main>

        <MarketingFooter />
    </div>
  )
}
