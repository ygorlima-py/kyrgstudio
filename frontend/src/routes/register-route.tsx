import { Link, useNavigate } from 'react-router'

import { RegisterForm } from '@/features/auth/components/register-form'

/**
 * Presents account registration and redirects authenticated users to the app.
 */
export function RegisterRoute() {
  const navigate = useNavigate()

  function handleRegistrationSuccess(): void {
    navigate('/app', { replace: true })
  }

  return (
    <div>
      <p className="font-mono text-meta uppercase tracking-[0.16em] text-action">
        Create your workspace
      </p>

      <h1 className="mt-3 font-heading text-heading-xl text-text">
        Create your account
      </h1>

      <p className="mt-3 text-body text-text-muted">
        Start analyzing and adapting sales messages for your offer.
      </p>

      <div className="mt-8">
        <RegisterForm onSuccess={handleRegistrationSuccess} />
      </div>

      <p className="mt-6 text-center text-body-sm text-text-muted">
        Already have an account?{' '}
        <Link
          className="font-semibold text-action underline-offset-4 hover:underline"
          to="/login"
        >
          Log in
        </Link>
      </p>
    </div>
  )
}