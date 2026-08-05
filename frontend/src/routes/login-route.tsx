import { Link, useLocation, useNavigate } from 'react-router'

import { LoginForm } from '@/features/auth/components/login-form'

import { SessionExpired } from '@/features/auth/components/session-expired'

/**
 * Presents password login and redirects authenticated users to the app.
 */
export function LoginRoute() {
  const navigate = useNavigate()
  const location = useLocation()
  const sessionExpired = isExpiredSessionState(location.state)

  function handleLoginSuccess(): void {
    navigate(getSafeReturnPath(location.state), { replace: true })  
}

  return (
    <div>
      <p className="text-center font-mono text-meta uppercase tracking-[0.16em] text-action">
        Welcome back
      </p>

      <h1 className="text-center font-heading text-[2.25rem] leading-none font-semibold text-text">
        Log in to your account
      </h1>

      <p className="text-center mt-3 text-body text-text-muted">
        Continue analyzing references and building adaptations for your offers.
      </p>

      {sessionExpired ? (
        <div className="mt-6">
          <SessionExpired />
        </div>
      ) : null}

      <div className="mt-8">
        <LoginForm onSuccess={handleLoginSuccess} />
      </div>

      <p className="mt-6 text-center text-body-sm text-text-muted">
        Do not have an account?{' '}
        <Link
          className="font-semibold text-action underline-offset-4 hover:underline"
          to="/register"
        >
          Create account
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