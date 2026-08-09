import { Navigate, Outlet, useLocation } from 'react-router'
import { useTranslation } from 'react-i18next'

import { LoadingState } from '@/shared/components/states/loading-state'

import { useAuth } from '../hooks/use-auth'

/**
 * Allows protected routes only after the authentication session is restored.
 */
export function RequireAuthentication() {
  const { t } = useTranslation()
  const session = useAuth()
  const location = useLocation()

  if (session.status === 'restoring') {
    return (
      <main className="mx-auto w-full max-w-6xl px-6 py-16">
        <LoadingState label={t('auth.session.restoring')} />
      </main>
    )
  }

  if (session.status === 'authenticated') {
    return <Outlet />
  }

  const returnTo = `${location.pathname}${location.search}${location.hash}`

  return (
    <Navigate
      replace
      state={{
        reason:
          session.status === 'expired'
            ? 'session-expired'
            : 'authentication-required',
        returnTo,
      }}
      to="/login"
    />
  )
}
