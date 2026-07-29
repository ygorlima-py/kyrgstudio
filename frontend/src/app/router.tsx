import { createBrowserRouter } from 'react-router'

import { LandingRoute } from '@/routes/landing-route'
import { NotFoundRoute } from '@/routes/not-found-route'

export const router = createBrowserRouter([
  {
    path: '/',
    Component: LandingRoute,
  },
  {
    path: '*',
    Component: NotFoundRoute,
  },
])
