import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import { LandingRoute } from '@/routes/landing-route'

describe('LandingRoute', () => {
  it('renders the product name', () => {
    render(<LandingRoute />)

    expect(screen.getByRole('heading', { name: 'Kyrg Studio' })).toBeInTheDocument()
  })
})
