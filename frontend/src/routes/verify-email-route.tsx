import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router'

import {
  EmailVerificationPending,
  type EmailVerificationFeedback,
} from '@/features/auth/components/email-verification-pending'
import { useAuth } from '@/features/auth/hooks/use-auth'
import {
  clearPendingVerificationEmail,
  resolvePendingVerificationEmail,
  storePendingVerificationEmail,
} from '@/features/auth/utils/pending-verification-email'

const RESEND_COOLDOWN_SECONDS = 60

/**
 * Coordinates email-verification guidance and controlled resend requests.
 */
export function VerifyEmailRoute() {
  const location = useLocation()
  const navigate = useNavigate()
  const { resendEmailVerification } = useAuth()
  const [email] = useState<string | null>(() => resolvePendingVerificationEmail(location.state))
  const [feedback, setFeedback] = useState<EmailVerificationFeedback>(null)
  const [isResending, setIsResending] = useState(false)
  const [cooldownSeconds, setCooldownSeconds] = useState(0)

  useEffect(() => {
    if (email !== null) {
      storePendingVerificationEmail(email)
    }
  }, [email])

  useEffect(() => {
    if (cooldownSeconds === 0) {
      return undefined
    }

    const timer = window.setTimeout(() => {
      setCooldownSeconds((currentSeconds) => Math.max(0, currentSeconds - 1))
    }, 1_000)

    return () => {
      window.clearTimeout(timer)
    }
  }, [cooldownSeconds])

  async function handleResend(): Promise<void> {
    if (email === null || isResending || cooldownSeconds > 0) {
      return
    }

    setFeedback(null)
    setIsResending(true)

    try {
      await resendEmailVerification({ email })
      setFeedback('resent')
      setCooldownSeconds(RESEND_COOLDOWN_SECONDS)
    } catch {
      setFeedback('error')
    } finally {
      setIsResending(false)
    }
  }

  function handleChangeEmail(): void {
    clearPendingVerificationEmail()
    navigate('/register', { replace: true })
  }

  return (
    <EmailVerificationPending
      cooldownSeconds={cooldownSeconds}
      email={email}
      feedback={feedback}
      isResending={isResending}
      onChangeEmail={handleChangeEmail}
      onResend={() => {
        void handleResend()
      }}
    />
  )
}
