import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'
import { describe, expect, it } from 'vitest'

import { LandingRoute } from '@/routes/landing-route'

describe('LandingRoute', () => {
  it('renders the landing page headline', () => {
    render(
      <MemoryRouter>
        <LandingRoute />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('heading', {
        name: 'See the strategy inside any sales video. Then make it yours.',
      }),
    ).toBeInTheDocument()
  })
})
