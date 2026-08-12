import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it } from 'vitest'

import { LandingRoute } from '@/routes/landing-route'
import { i18n } from '@/shared/i18n/i18n'

describe('LandingRoute', () => {
  beforeEach(async () => {
    await i18n.changeLanguage('en')
  })

  it('renders the landing page headline', () => {
    render(
      <MemoryRouter>
        <LandingRoute />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('heading', {
        name: 'Analyze Any Sales Video. Adapt the Strategy to Your Offer.',
      }),
    ).toBeInTheDocument()
  })
})
