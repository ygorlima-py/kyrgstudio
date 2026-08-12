import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { ForgotPasswordForm } from '@/features/auth/components/forgot-password-form'

/** Presents the neutral password-recovery request flow. */
export function ForgotPasswordRoute() {
  const { t } = useTranslation()

  return (
    <div>
      <p className="text-center font-mono text-meta uppercase tracking-[0.16em] text-action">
        {t('auth.forgotPassword.page.eyebrow')}
      </p>

      <h1
        className="mt-3 text-center font-heading text-[2.25rem] leading-none font-semibold text-text"
        id="forgot-password-title"
      >
        {t('auth.forgotPassword.page.title')}
      </h1>

      <p className="mt-3 text-center text-body text-text-muted">
        {t('auth.forgotPassword.page.description')}
      </p>

      <div className="mt-8">
        <ForgotPasswordForm />
      </div>

      <p className="mt-6 text-center text-body-sm text-text-muted">
        {t('auth.forgotPassword.page.rememberedPrompt')}{' '}
        <Link className="font-semibold text-action underline-offset-4 hover:underline" to="/login">
          {t('auth.forgotPassword.page.login')}
        </Link>
      </p>
    </div>
  )
}
