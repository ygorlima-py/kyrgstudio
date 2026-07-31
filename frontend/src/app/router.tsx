import { createBrowserRouter } from 'react-router'
import { MarketingLayout } from '@/layouts/marketing-layout'

import { LandingRoute } from '@/routes/landing-route'
import { NotFoundRoute } from '@/routes/not-found-route'

import { AuthLayout } from '@/layouts/auth-layout'
import { RegisterRoute } from '@/routes/register-route'
import { LoginRoute } from '@/routes/login-route'
import { RequireAuthentication } from '@/features/auth/components/require-authentication'


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
    Component: AuthLayout,
    children: [
      {
        path: '/register',
        Component: RegisterRoute,
      },
      {
      path: '/login',
      Component: LoginRoute,
      },
    ],
  },
  {
    path: '/app',
    Component: RequireAuthentication,
  },
  {
    path: '*',
    Component: NotFoundRoute,
  },
])
