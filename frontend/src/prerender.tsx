import { StrictMode } from 'react'
import { renderToString } from 'react-dom/server'
import { createMemoryRouter } from 'react-router'

import { App } from '@/app/app'
import { applicationRoutes } from '@/app/route-config'
import { i18n, type SupportedLanguage } from '@/shared/i18n/i18n'

/**
 * Renders one localized landing page during the production build.
 */
export async function renderLandingPage(
  pathname: string,
  language: SupportedLanguage,
): Promise<string> {
  await i18n.changeLanguage(language)

  const router = createMemoryRouter(applicationRoutes, {
    initialEntries: [pathname],
  })

  return renderToString(
    <StrictMode>
      <App applicationRouter={router} />
    </StrictMode>,
  )
}
