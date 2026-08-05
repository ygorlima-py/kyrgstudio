import type { RouteObject } from 'react-router'

import { RequireAuthentication } from '@/features/auth/components/require-authentication'
import { AppLayout } from '@/layouts/app-layout'
import { AuthLayout } from '@/layouts/auth-layout'
import { MarketingLayout } from '@/layouts/marketing-layout'
import { DashboardRoute } from '@/routes/dashboard-route'
import { JobResultRoute } from '@/routes/job-result-route'
import { JobsHistoryRoute } from '@/routes/jobs-history-route'
import { JobStatusRoute } from '@/routes/job-status-route'
import { LandingRoute } from '@/routes/landing-route'
import { LoginRoute } from '@/routes/login-route'
import { NewJobRoute } from '@/routes/new-job-route'
import { NotFoundRoute } from '@/routes/not-found-route'
import { RegisterRoute } from '@/routes/register-route'

/** Shared route tree used by both the browser and the production prerenderer. */
export const applicationRoutes: RouteObject[] = [
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
    path: '/pt-BR',
    Component: MarketingLayout,
    children: [
      {
        index: true,
        Component: LandingRoute,
      },
    ],
  },
  {
    path: '/en',
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
            path: 'jobs',
            Component: JobsHistoryRoute,
          },
          {
            path: 'jobs/:jobId',
            Component: JobStatusRoute,
          },
          {
            path: 'jobs/:jobId/result',
            Component: JobResultRoute,
          },
        ],
      },
    ],
  },
  {
    path: '*',
    Component: NotFoundRoute,
  },
]
