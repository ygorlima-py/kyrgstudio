import { Link, useLocation, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'

import { LoginForm } from '@/features/auth/components/login-form'

import { SessionExpired } from '@/features/auth/components/session-expired'

/**
 * Presents password login and redirects authenticated users to the app.
 */
export function LoginRoute() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const sessionExpired = isExpiredSessionState(location.state)

  function handleLoginSuccess(): void {
    navigate(getSafeReturnPath(location.state), { replace: true })
  }

  function handleEmailVerificationRequired(email: string): void {
    navigate('/verify-email', {
      replace: true,
      state: { email },
    })
  }

  return (
    <div>
      <p className="text-center font-mono text-meta uppercase tracking-[0.16em] text-action">
        {t('auth.login.page.eyebrow')}
      </p>

      <h1 className="text-center font-heading text-[2.25rem] leading-none font-semibold text-text">
        {t('auth.login.page.title')}
      </h1>

      <p className="mt-3 text-center text-body text-text-muted">
        {t('auth.login.page.description')}
      </p>

      {sessionExpired ? (
        <div className="mt-6">
          <SessionExpired />
        </div>
      ) : null}

      <div className="mt-8">
        <LoginForm
          onEmailVerificationRequired={handleEmailVerificationRequired}
          onSuccess={handleLoginSuccess}
        />
      </div>

      <p className="mt-6 text-center text-body-sm text-text-muted">
        {t('auth.login.page.registerPrompt')}{' '}
        <Link
          className="font-semibold text-action underline-offset-4 hover:underline"
          to="/register"
        >
          {t('auth.login.page.register')}
        </Link>
      </p>
    </div>
  )
}

function getSafeReturnPath(locationState: unknown): string {
  if (
    typeof locationState === 'object' &&
    locationState !== null &&
    'returnTo' in locationState &&
    typeof locationState.returnTo === 'string' &&
    locationState.returnTo.startsWith('/app')
  ) {
    return locationState.returnTo
  }

  return '/app'
}

function isExpiredSessionState(locationState: unknown): boolean {
  return (
    typeof locationState === 'object' &&
    locationState !== null &&
    'reason' in locationState &&
    locationState.reason === 'session-expired'
  )
}
