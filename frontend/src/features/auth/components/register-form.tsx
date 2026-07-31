import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import { useForm } from 'react-hook-form'

import { ApiError, type RegisterRequest } from '@/shared/api'
import { Alert } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { FieldMessage } from '@/shared/ui/field-message'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'

import { useAuth } from '../hooks/use-auth'
import {
  registerFormSchema,
  type RegisterFormData,
  type RegisterFormInput,
} from '../schemas/auth-schemas'

export interface RegisterFormProps {
  readonly onSuccess: () => void
}

/**
 * Collects and validates the information required to create a password account.
 */
export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const { registerWithPassword } = useAuth()
  const [submissionError, setSubmissionError] = useState<string | null>(null)

  const {
    formState: { errors, isSubmitting },
    handleSubmit,
    register,
  } = useForm<RegisterFormInput, unknown, RegisterFormData>({
    resolver: zodResolver(registerFormSchema),
    defaultValues: {
      name: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
  })

  async function submitRegistration(formData: RegisterFormData): Promise<void> {
    setSubmissionError(null)

    const request: RegisterRequest = {
      email: formData.email,
      password: formData.password,
      ...(formData.name !== undefined ? { name: formData.name } : {}),
    }

    try {
      await registerWithPassword(request)
      onSuccess()
    } catch (error) {
      setSubmissionError(registrationErrorMessage(error))
    }
  }

  return (
    <form
      className="space-y-5"
      noValidate
      onSubmit={handleSubmit(submitRegistration)}
    >
      {submissionError !== null ? (
        <Alert heading="Account could not be created" variant="danger">
          {submissionError}
        </Alert>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="register-name">Name</Label>
        <Input
          {...register('name')}
          aria-describedby={errors.name ? 'register-name-error' : undefined}
          aria-invalid={errors.name ? true : undefined}
          autoComplete="name"
          disabled={isSubmitting}
          id="register-name"
          placeholder="Your name"
        />
        {errors.name ? (
          <FieldMessage id="register-name-error" variant="error">
            {errors.name.message}
          </FieldMessage>
        ) : null}
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-email">Email</Label>
        <Input
          {...register('email')}
          aria-describedby={errors.email ? 'register-email-error' : undefined}
          aria-invalid={errors.email ? true : undefined}
          autoComplete="email"
          disabled={isSubmitting}
          id="register-email"
          inputMode="email"
          placeholder="you@example.com"
          type="email"
        />
        {errors.email ? (
          <FieldMessage id="register-email-error" variant="error">
            {errors.email.message}
          </FieldMessage>
        ) : null}
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-password">Password</Label>
        <Input
          {...register('password')}
          aria-describedby={errors.password ? 'register-password-error' : undefined}
          aria-invalid={errors.password ? true : undefined}
          autoComplete="new-password"
          disabled={isSubmitting}
          id="register-password"
          type="password"
        />
        {errors.password ? (
          <FieldMessage id="register-password-error" variant="error">
            {errors.password.message}
          </FieldMessage>
        ) : (
          <FieldMessage>Use at least 8 characters.</FieldMessage>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-confirm-password">Confirm password</Label>
        <Input
          {...register('confirmPassword')}
          aria-describedby={
            errors.confirmPassword ? 'register-confirm-password-error' : undefined
          }
          aria-invalid={errors.confirmPassword ? true : undefined}
          autoComplete="new-password"
          disabled={isSubmitting}
          id="register-confirm-password"
          type="password"
        />
        {errors.confirmPassword ? (
          <FieldMessage id="register-confirm-password-error" variant="error">
            {errors.confirmPassword.message}
          </FieldMessage>
        ) : null}
      </div>

      <Button
        className="w-full"
        isLoading={isSubmitting}
        loadingContent="Creating account..."
        type="submit"
      >
        Create account
      </Button>
    </form>
  )
}

function registrationErrorMessage(error: unknown): string {
  if (
    error instanceof ApiError &&
    error.code === 'invalid_input' &&
    error.details.code === 'already_exists'
  ) {
    return 'An account with this email already exists.'
  }

  if (error instanceof ApiError && error.status === null) {
    return 'We could not reach the server. Check your connection and try again.'
  }

  return 'Please review your information and try again.'
}