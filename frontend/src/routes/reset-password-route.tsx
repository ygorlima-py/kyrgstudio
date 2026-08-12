import { useEffect, useState } from 'react'
import { useLocation } from 'react-router'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { ResetPasswordForm } from '@/features/auth/components/reset-password-form'

/** Presents password replacement from a one-time email link. */
export function ResetPasswordRoute() {
  const { t } = useTranslation()
  const location = useLocation()
  const [token] = useState<string | null>(() => readTokenFromFragment(location.hash))

  useEffect(() => {
    if (token === null || typeof window === 'undefined' || window.location.hash === '') {
      return
    }

    window.history.replaceState(
      null,
      '',
      `${window.location.pathname}${window.location.search}`,
    )
  }, [token])

  return (
    <div>
      <p className="text-center font-mono text-meta uppercase tracking-[0.16em] text-action">
        {t('auth.resetPassword.page.eyebrow')}
      </p>

      <h1
        className="mt-3 text-center font-heading text-[2.25rem] leading-none font-semibold text-text"
        id="reset-password-title"
      >
        {t('auth.resetPassword.page.title')}
      </h1>

      <p className="mt-3 text-center text-body text-text-muted">
        {token === null
          ? t('auth.resetPassword.missingToken.description')
          : t('auth.resetPassword.page.description')}
      </p>

      <div className="mt-8">
        {token === null ? <MissingResetToken /> : <ResetPasswordForm token={token} />}
      </div>
    </div>
  )
}

function MissingResetToken() {
  const { t } = useTranslation()

  return (
    <section aria-labelledby="reset-password-missing-title" className="space-y-6">
      <div
        aria-live="polite"
        className="rounded-md border border-danger bg-danger-muted px-4 py-3 text-body-sm text-danger"
        id="reset-password-missing-title"
        role="alert"
      >
        {t('auth.resetPassword.missingToken.message')}
      </div>

      <div className="space-y-3">
        <Link
          className="flex min-h-12 items-center justify-center rounded-md bg-action px-6 text-label text-text-inverse shadow-sm transition-colors hover:bg-action-hover focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          to="/forgot-password"
        >
          {t('auth.resetPassword.actions.requestNewLink')}
        </Link>

        <Link
          className="flex min-h-11 items-center justify-center text-label font-semibold text-action underline-offset-4 hover:underline"
          to="/login"
        >
          {t('auth.resetPassword.actions.returnToLogin')}
        </Link>
      </div>
    </section>
  )
}

function readTokenFromFragment(fragment: string): string | null {
  const fragmentValue = fragment.startsWith('#') ? fragment.slice(1) : fragment

  if (fragmentValue.length === 0) {
    return null
  }

  const token = new URLSearchParams(fragmentValue).get('token')?.trim()

  return token === undefined || token.length === 0 ? null : token
}
