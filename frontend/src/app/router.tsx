import { createBrowserRouter } from 'react-router'
import { MarketingLayout } from '@/layouts/marketing-layout'

import { LandingRoute } from '@/routes/landing-route'
import { NotFoundRoute } from '@/routes/not-found-route'

import { AuthLayout } from '@/layouts/auth-layout'
import { RegisterRoute } from '@/routes/register-route'
import { LoginRoute } from '@/routes/login-route'
import { RequireAuthentication } from '@/features/auth/components/require-authentication'

import { AppLayout } from '@/layouts/app-layout'
import { DashboardRoute } from '@/routes/dashboard-route'

import { NewJobRoute } from '@/routes/new-job-route'
import { JobStatusRoute } from '@/routes/job-status-route'

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
    Component: RequireAuthentication,
    children: [
      {
        path: '/app',
        Component: AppLayout,
        children: [
          {
            index: true,
            Component: DashboardRoute,
          },
          {
            path: 'jobs/new',
            Component: NewJobRoute,
          },
          {
            path: 'jobs/:jobId',
            Component: JobStatusRoute,
          },
        ],
      },
    ],
  },
  {
    path: '*',
    Component: NotFoundRoute,
  },
])
