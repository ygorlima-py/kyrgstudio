import { useTranslation } from 'react-i18next'
import { Link, useNavigate } from 'react-router'

import { RegisterForm } from '@/features/auth/components/register-form'

/**
 * Presents account registration and redirects authenticated users to the app.
 */
export function RegisterRoute() {
  const { t } = useTranslation()
  const navigate = useNavigate()

  function handleRegistrationSuccess(): void {
    navigate('/app', { replace: true })
  }

  return (
    <div>
      <h1 className="text-center font-heading text-[2.25rem] leading-none font-semibold text-text">
        {t('auth.register.title')}
      </h1>

      <div className="mt-8">
        <RegisterForm onSuccess={handleRegistrationSuccess} />
      </div>

      <p className="mt-6 text-center text-body-sm text-text-muted">
        {t('auth.register.loginPrompt')}{' '}

        <Link
          className="font-semibold text-action underline-offset-4 hover:underline"
          to="/login"
        >
          {t('auth.register.login')}
        </Link>
      </p>
    </div>
  )
}