import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'

import { resetPassword } from '@/features/auth/api/auth-api'
import { ApiError, type ResetPasswordRequest } from '@/shared/api'
import { Alert } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { FieldMessage } from '@/shared/ui/field-message'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'

import {
  resetPasswordFormSchema,
  type ResetPasswordFormData,
  type ResetPasswordFormInput,
} from '../schemas/auth-schemas'

const validationTranslationKeys: Readonly<Record<string, string>> = {
  'Password must contain at least 8 characters.':
    'auth.resetPassword.validation.passwordMinimum',
  'Password must contain at most 128 characters.':
    'auth.resetPassword.validation.passwordMaximum',
  'Passwords do not match.': 'auth.resetPassword.validation.passwordMismatch',
}

export interface ResetPasswordFormProps {
  readonly token: string
}

type PasswordResetErrorKind = 'invalidToken' | 'temporary' | 'generic'

/** Replaces the password using the one-time token kept in memory. */
export function ResetPasswordForm({ token }: ResetPasswordFormProps) {
  const { t } = useTranslation()
  const [submissionError, setSubmissionError] = useState<PasswordResetErrorKind | null>(null)
  const [isResetSuccessful, setIsResetSuccessful] = useState(false)

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
  } = useForm<ResetPasswordFormInput, unknown, ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordFormSchema),
    defaultValues: {
      newPassword: '',
      confirmPassword: '',
    },
  })

  async function submitPasswordReset(formData: ResetPasswordFormData): Promise<void> {
    setSubmissionError(null)

    const request: ResetPasswordRequest = {
      token,
      new_password: formData.newPassword,
    }

    try {
      await resetPassword(request)
      setIsResetSuccessful(true)
    } catch (error) {
      setSubmissionError(passwordResetErrorKind(error))
    }
  }

  if (isResetSuccessful) {
    return (
      <section aria-labelledby="reset-password-success-title" className="space-y-6">
        <Alert heading={t('auth.resetPassword.success.heading')} variant="success">
          <p aria-live="polite" id="reset-password-success-title" role="status">
            {t('auth.resetPassword.success.description')}
          </p>
        </Alert>

        <Link
          className="flex min-h-12 items-center justify-center rounded-md bg-action px-6 text-label text-text-inverse shadow-sm transition-colors hover:bg-action-hover focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          to="/login"
        >
          {t('auth.resetPassword.actions.returnToLogin')}
        </Link>
      </section>
    )
  }

  if (submissionError === 'invalidToken') {
    return <InvalidResetTokenState />
  }

  return (
    <form className="space-y-5" noValidate onSubmit={handleSubmit(submitPasswordReset)}>
      {submissionError !== null ? (
        <Alert heading={t('auth.resetPassword.errors.heading')} variant="danger">
          <p aria-live="polite" role="alert">
            {t(passwordResetErrorMessageKey(submissionError))}
          </p>
        </Alert>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="reset-password-new-password">
          {t('auth.resetPassword.fields.newPassword')}
        </Label>

        <Input
          {...register('newPassword')}
          aria-describedby={
            errors.newPassword
              ? 'reset-password-new-password-error'
              : 'reset-password-new-password-hint'
          }
          aria-invalid={errors.newPassword ? true : undefined}
          autoComplete="new-password"
          disabled={isSubmitting}
          id="reset-password-new-password"
          type="password"
        />

        {errors.newPassword ? (
          <FieldMessage id="reset-password-new-password-error" variant="error">
            {validationErrorMessage(errors.newPassword.message, t)}
          </FieldMessage>
        ) : (
          <FieldMessage id="reset-password-new-password-hint">
            {t('auth.resetPassword.fields.passwordHint')}
          </FieldMessage>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="reset-password-confirm-password">
          {t('auth.resetPassword.fields.confirmPassword')}
        </Label>

        <Input
          {...register('confirmPassword')}
          aria-describedby={errors.confirmPassword ? 'reset-password-confirm-password-error' : undefined}
          aria-invalid={errors.confirmPassword ? true : undefined}
          autoComplete="new-password"
          disabled={isSubmitting}
          id="reset-password-confirm-password"
          type="password"
        />

        {errors.confirmPassword ? (
          <FieldMessage id="reset-password-confirm-password-error" variant="error">
            {validationErrorMessage(errors.confirmPassword.message, t)}
          </FieldMessage>
        ) : null}
      </div>

      <Button
        className="w-full"
        isLoading={isSubmitting}
        loadingContent={t('auth.resetPassword.actions.saving')}
        size="lg"
        type="submit"
      >
        {submissionError === 'temporary'
          ? t('auth.resetPassword.actions.tryAgain')
          : t('auth.resetPassword.actions.submit')}
      </Button>
    </form>
  )
}

function InvalidResetTokenState() {
  const { t } = useTranslation()

  return (
    <section aria-labelledby="reset-password-invalid-token-title" className="space-y-6">
      <Alert heading={t('auth.resetPassword.errors.heading')} variant="danger">
        <p aria-live="polite" id="reset-password-invalid-token-title" role="alert">
          {t('auth.resetPassword.errors.invalidToken')}
        </p>
      </Alert>

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

function validationErrorMessage(message: string | undefined, t: TFunction): string {
  if (message === undefined) {
    return t('auth.resetPassword.errors.invalidData')
  }

  const translationKey = validationTranslationKeys[message]

  return translationKey !== undefined
    ? t(translationKey)
    : t('auth.resetPassword.errors.invalidData')
}

function passwordResetErrorKind(error: unknown): PasswordResetErrorKind {
  if (error instanceof ApiError && error.code === 'invalid_input') {
    return 'invalidToken'
  }

  if (error instanceof ApiError && error.retryable) {
    return 'temporary'
  }

  return 'generic'
}

function passwordResetErrorMessageKey(errorKind: PasswordResetErrorKind): string {
  if (errorKind === 'temporary') {
    return 'auth.resetPassword.errors.temporary'
  }

  return 'auth.resetPassword.errors.generic'
}
