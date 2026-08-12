import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'

import { requestPasswordReset } from '@/features/auth/api/auth-api'
import { ApiError, type ForgotPasswordRequest } from '@/shared/api'
import { Alert } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { FieldMessage } from '@/shared/ui/field-message'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'

import {
  forgotPasswordFormSchema,
  type ForgotPasswordFormData,
  type ForgotPasswordFormInput,
} from '../schemas/auth-schemas'

const validationTranslationKeys: Readonly<Record<string, string>> = {
  'Email is required.': 'auth.forgotPassword.validation.emailRequired',
  'Email is too long.': 'auth.forgotPassword.validation.emailTooLong',
  'Enter a valid email address.': 'auth.forgotPassword.validation.emailInvalid',
}

/**
 * Requests account recovery without revealing whether an email is registered.
 */
export function ForgotPasswordForm() {
  const { t } = useTranslation()
  const [submissionError, setSubmissionError] = useState<string | null>(null)
  const [submittedEmail, setSubmittedEmail] = useState<string | null>(null)

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
    reset,
  } = useForm<ForgotPasswordFormInput, unknown, ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordFormSchema),
    defaultValues: {
      email: '',
    },
  })

  async function submitForgotPassword(formData: ForgotPasswordFormData): Promise<void> {
    setSubmissionError(null)

    const request: ForgotPasswordRequest = {
      email: formData.email,
    }

    try {
      await requestPasswordReset(request)
      setSubmittedEmail(request.email)
    } catch (error) {
      setSubmissionError(forgotPasswordErrorMessage(error, t))
    }
  }

  function startAnotherRequest(): void {
    setSubmittedEmail(null)
    setSubmissionError(null)
    reset()
  }

  if (submittedEmail !== null) {
    return (
      <section aria-labelledby="forgot-password-success-title" className="space-y-6">
        <Alert heading={t('auth.forgotPassword.success.heading')} variant="success">
          <p aria-live="polite" id="forgot-password-success-title" role="status">
            {t('auth.forgotPassword.success.description', {
              email: submittedEmail,
            })}
          </p>
        </Alert>

        <div className="space-y-3">
          <Button className="w-full" onClick={startAnotherRequest} size="lg" variant="secondary">
            {t('auth.forgotPassword.actions.tryAnotherEmail')}
          </Button>

          <Link
            className="flex min-h-11 items-center justify-center text-label font-semibold text-action underline-offset-4 hover:underline"
            to="/login"
          >
            {t('auth.forgotPassword.actions.returnToLogin')}
          </Link>
        </div>
      </section>
    )
  }

  return (
    <form className="space-y-5" noValidate onSubmit={handleSubmit(submitForgotPassword)}>
      {submissionError !== null ? (
        <Alert heading={t('auth.forgotPassword.errors.heading')} variant="danger">
          {submissionError}
        </Alert>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="forgot-password-email">{t('auth.forgotPassword.fields.email')}</Label>

        <Input
          {...register('email')}
          aria-describedby={errors.email ? 'forgot-password-email-error' : undefined}
          aria-invalid={errors.email ? true : undefined}
          autoComplete="email"
          disabled={isSubmitting}
          id="forgot-password-email"
          inputMode="email"
          placeholder={t('auth.forgotPassword.fields.emailPlaceholder')}
          type="email"
        />

        {errors.email ? (
          <FieldMessage id="forgot-password-email-error" variant="error">
            {validationErrorMessage(errors.email.message, t)}
          </FieldMessage>
        ) : null}
      </div>

      <Button
        className="w-full"
        isLoading={isSubmitting}
        loadingContent={t('auth.forgotPassword.actions.sending')}
        size="lg"
        type="submit"
      >
        {t('auth.forgotPassword.actions.submit')}
      </Button>
    </form>
  )
}

function validationErrorMessage(message: string | undefined, t: TFunction): string {
  if (message === undefined) {
    return t('auth.forgotPassword.errors.invalidData')
  }

  const translationKey = validationTranslationKeys[message]

  return translationKey !== undefined
    ? t(translationKey)
    : t('auth.forgotPassword.errors.invalidData')
}

function forgotPasswordErrorMessage(error: unknown, t: TFunction): string {
  if (error instanceof ApiError && error.status === null) {
    return t('auth.forgotPassword.errors.network')
  }

  return t('auth.forgotPassword.errors.generic')
}
