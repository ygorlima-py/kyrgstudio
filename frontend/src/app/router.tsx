import { createBrowserRouter } from 'react-router'
import { MarketingLayout } from '@/layouts/marketing-layout'

import { LandingRoute } from '@/routes/landing-route'
import { NotFoundRoute } from '@/routes/not-found-route'

export const router = createBrowserRouter([
  {
    path: '/',
    Component: MarketingLayout,
    children: [
      {
        index: true,
        Component: LandingRoute,
      },
    ],
  },
  {
    path: '*',
    Component: NotFoundRoute,
  },
])
