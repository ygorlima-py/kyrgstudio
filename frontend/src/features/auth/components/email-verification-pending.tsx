import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { Button } from '@/shared/ui/button'

export type EmailVerificationFeedback = 'resent' | 'error' | null

export interface EmailVerificationPendingProps {
  readonly cooldownSeconds: number
  readonly email: string | null
  readonly feedback: EmailVerificationFeedback
  readonly isResending: boolean
  readonly onChangeEmail: () => void
  readonly onResend: () => void
}

/**
 * Presents the next steps while an account waits for email confirmation.
 */
export function EmailVerificationPending({
  cooldownSeconds,
  email,
  feedback,
  isResending,
  onChangeEmail,
  onResend,
}: EmailVerificationPendingProps) {
  const { t } = useTranslation()
  const canResend = email !== null && cooldownSeconds === 0

  return (
    <section aria-labelledby="email-verification-title" className="text-center">
      <VerificationIcon />

      <p className="mt-6 font-mono text-meta uppercase tracking-[0.16em] text-action">
        {t('auth.emailVerification.eyebrow')}
      </p>

      <h1
        className="mt-3 font-heading text-[2.25rem] leading-none font-semibold text-text"
        id="email-verification-title"
      >
        {email === null
          ? t('auth.emailVerification.missingEmail.title')
          : t('auth.emailVerification.title')}
      </h1>

      <p className="mx-auto mt-4 max-w-sm text-body text-text-muted">
        {email === null
          ? t('auth.emailVerification.missingEmail.description')
          : t('auth.emailVerification.description')}
      </p>

      {email !== null ? (
        <p className="mt-4 break-all text-body font-semibold text-text">{email}</p>
      ) : null}

      {email !== null ? <VerificationSteps /> : null}

      <div className="mt-8 space-y-3">
        {email !== null ? (
          <Button
            className="w-full text-text-inverse"
            disabled={!canResend}
            isLoading={isResending}
            loadingContent={t('auth.emailVerification.actions.resending')}
            onClick={onResend}
            size="lg"
          >
            {cooldownSeconds > 0
              ? t('auth.emailVerification.actions.resendIn', {
                  seconds: cooldownSeconds,
                })
              : t('auth.emailVerification.actions.resend')}
          </Button>
        ) : (
          <Button className="w-full text-text-inverse" onClick={onChangeEmail} size="lg">
            {t('auth.emailVerification.actions.returnToRegistration')}
          </Button>
        )}

        {email !== null ? (
          <Button className="w-full" onClick={onChangeEmail} size="lg" variant="ghost">
            {t('auth.emailVerification.actions.changeEmail')}
          </Button>
        ) : null}
      </div>

      <VerificationFeedback feedback={feedback} />

      <p className="mt-8 text-body-sm text-text-muted">
        {t('auth.emailVerification.loginPrompt')}{' '}
        <Link className="font-semibold text-action underline-offset-4 hover:underline" to="/login">
          {t('auth.emailVerification.actions.login')}
        </Link>
      </p>
    </section>
  )
}

function VerificationSteps() {
  const { t } = useTranslation()

  return (
    <ol className="mt-8 border-y border-border text-left">
      {(['openInbox', 'followLink', 'enterWorkspace'] as const).map((step, index) => (
        <li
          className="grid grid-cols-[2rem_1fr] gap-3 border-b border-border py-4 last:border-b-0"
          key={step}
        >
          <span className="font-mono text-meta text-action">0{index + 1}</span>
          <span className="text-body-sm text-text-muted">
            {t(`auth.emailVerification.steps.${step}`)}
          </span>
        </li>
      ))}
    </ol>
  )
}

function VerificationFeedback({ feedback }: { readonly feedback: EmailVerificationFeedback }) {
  const { t } = useTranslation()

  if (feedback === null) {
    return null
  }

  return (
    <p
      aria-live="polite"
      className={
        feedback === 'resent' ? 'mt-5 text-body-sm text-success' : 'mt-5 text-body-sm text-danger'
      }
      role={feedback === 'error' ? 'alert' : 'status'}
    >
      {feedback === 'resent'
        ? t('auth.emailVerification.feedback.resent')
        : t('auth.emailVerification.feedback.error')}
    </p>
  )
}

function VerificationIcon() {
  return (
    <div
      aria-hidden="true"
      className="mx-auto flex size-16 items-center justify-center rounded-pill border border-action text-action"
    >
      <svg className="size-7" fill="none" viewBox="0 0 24 24">
        <path
          d="m4 7 8 6 8-6M5.5 19h13A1.5 1.5 0 0 0 20 17.5v-11A1.5 1.5 0 0 0 18.5 5h-13A1.5 1.5 0 0 0 4 6.5v11A1.5 1.5 0 0 0 5.5 19Z"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="1.5"
        />
      </svg>
    </div>
  )
}
