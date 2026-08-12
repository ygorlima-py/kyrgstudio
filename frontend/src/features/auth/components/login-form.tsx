import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router'

import { ApiError, type PasswordLoginRequest } from '@/shared/api'
import { Alert } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { FieldMessage } from '@/shared/ui/field-message'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'

import { useAuth } from '../hooks/use-auth'
import { loginFormSchema, type LoginFormData, type LoginFormInput } from '../schemas/auth-schemas'

const validationTranslationKeys: Readonly<Record<string, string>> = {
  'Email is required.': 'auth.login.validation.emailRequired',
  'Email is too long.': 'auth.login.validation.emailTooLong',
  'Enter a valid email address.': 'auth.login.validation.emailInvalid',
  'Password must contain at least 8 characters.': 'auth.login.validation.passwordMinimum',
  'Password must contain at most 128 characters.': 'auth.login.validation.passwordMaximum',
}

export interface LoginFormProps {
  readonly onEmailVerificationRequired: (email: string) => void
  readonly onSuccess: () => void
}

/**
 * Validates credentials and starts an authenticated application session.
 */
export function LoginForm({ onEmailVerificationRequired, onSuccess }: LoginFormProps) {
  const { t } = useTranslation()
  const { loginWithPassword } = useAuth()
  const [submissionError, setSubmissionError] = useState<string | null>(null)

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
  } = useForm<LoginFormInput, unknown, LoginFormData>({
    resolver: zodResolver(loginFormSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  })

  async function submitLogin(formData: LoginFormData): Promise<void> {
    setSubmissionError(null)

    const request: PasswordLoginRequest = {
      email: formData.email,
      password: formData.password,
    }

    try {
      await loginWithPassword(request)
      onSuccess()
    } catch (error) {
      if (isEmailVerificationRequired(error)) {
        onEmailVerificationRequired(request.email)
        return
      }

      setSubmissionError(loginErrorMessage(error, t))
    }
  }

  return (
    <form className="space-y-5" noValidate onSubmit={handleSubmit(submitLogin)}>
      {submissionError !== null ? (
        <Alert heading={t('auth.login.errors.heading')} variant="danger">
          {submissionError}
        </Alert>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="login-email">{t('auth.login.fields.email')}</Label>
        <Input
          {...register('email')}
          aria-describedby={errors.email ? 'login-email-error' : undefined}
          aria-invalid={errors.email ? true : undefined}
          autoComplete="email"
          disabled={isSubmitting}
          id="login-email"
          inputMode="email"
          placeholder={t('auth.login.fields.emailPlaceholder')}
          type="email"
        />
        {errors.email ? (
          <FieldMessage id="login-email-error" variant="error">
            {validationErrorMessage(errors.email.message, t)}
          </FieldMessage>
        ) : null}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-4">
          <Label htmlFor="login-password">{t('auth.login.fields.password')}</Label>
          <Link
            className="text-body-sm text-action underline-offset-4 hover:underline"
            to="/forgot-password"
          >
            {t('auth.login.fields.forgotPassword')}
          </Link>
        </div>

        <Input
          {...register('password')}
          aria-describedby={errors.password ? 'login-password-error' : undefined}
          aria-invalid={errors.password ? true : undefined}
          autoComplete="current-password"
          disabled={isSubmitting}
          id="login-password"
          type="password"
        />
        {errors.password ? (
          <FieldMessage id="login-password-error" variant="error">
            {validationErrorMessage(errors.password.message, t)}
          </FieldMessage>
        ) : null}
      </div>

      <Button
        className="w-full"
        isLoading={isSubmitting}
        loadingContent={t('auth.login.actions.loggingIn')}
        type="submit"
      >
        {t('auth.login.actions.submit')}
      </Button>
    </form>
  )
}

function isEmailVerificationRequired(error: unknown): boolean {
  return error instanceof ApiError && error.code === 'email_verification_required'
}

function validationErrorMessage(message: string | undefined, t: TFunction): string {
  if (message === undefined) {
    return t('auth.login.errors.generic')
  }

  const translationKey = validationTranslationKeys[message]

  return translationKey !== undefined ? t(translationKey) : message
}

function loginErrorMessage(error: unknown, t: TFunction): string {
  if (error instanceof ApiError && error.code === 'invalid_credentials') {
    return t('auth.login.errors.invalidCredentials')
  }

  if (error instanceof ApiError && error.code === 'account_disabled') {
    return t('auth.login.errors.accountDisabled')
  }

  if (error instanceof ApiError && error.status === null) {
    return t('auth.login.errors.network')
  }

  return t('auth.login.errors.generic')
}
