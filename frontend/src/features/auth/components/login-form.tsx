import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'

import { ApiError, type PasswordLoginRequest } from '@/shared/api'
import { Alert } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { FieldMessage } from '@/shared/ui/field-message'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'

import { useAuth } from '../hooks/use-auth'
import {
  loginFormSchema,
  type LoginFormData,
  type LoginFormInput,
} from '../schemas/auth-schemas'

export interface LoginFormProps {
  readonly onSuccess: () => void
}

/**
 * Validates credentials and starts an authenticated application session.
 */
export function LoginForm({ onSuccess }: LoginFormProps) {
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
      setSubmissionError(loginErrorMessage(error))
    }
  }

  return (
    <form className="space-y-5" noValidate onSubmit={handleSubmit(submitLogin)}>
      {submissionError !== null ? (
        <Alert heading="Login failed" variant="danger">
          {submissionError}
        </Alert>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="login-email">Email</Label>
        <Input
          {...register('email')}
          aria-describedby={errors.email ? 'login-email-error' : undefined}
          aria-invalid={errors.email ? true : undefined}
          autoComplete="email"
          disabled={isSubmitting}
          id="login-email"
          inputMode="email"
          placeholder="you@example.com"
          type="email"
        />
        {errors.email ? (
          <FieldMessage id="login-email-error" variant="error">
            {errors.email.message}
          </FieldMessage>
        ) : null}
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-4">
          <Label htmlFor="login-password">Password</Label>
          <span className="text-body-sm text-text-subtle">
            Forgot password?
          </span>
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
            {errors.password.message}
          </FieldMessage>
        ) : null}
      </div>

      <Button
        className="w-full"
        isLoading={isSubmitting}
        loadingContent="Logging in..."
        type="submit"
      >
        Log in
      </Button>
    </form>
  )
}

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code === 'invalid_credentials') {
    return 'Email or password is incorrect.'
  }

  if (error instanceof ApiError && error.code === 'account_disabled') {
    return 'This account is currently disabled.'
  }

  if (
    error instanceof ApiError &&
    error.code === 'email_verification_required'
  ) {
    return 'Verify your email before logging in.'
  }

  if (error instanceof ApiError && error.status === null) {
    return 'We could not reach the server. Check your connection and try again.'
  }

  return 'Login could not be completed. Please try again.'
}