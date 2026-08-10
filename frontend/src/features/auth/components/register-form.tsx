import { useState } from 'react'
import { zodResolver } from '@hookform/resolvers/zod'
import type { TFunction } from 'i18next'
import { useTranslation } from 'react-i18next'
import { useForm } from 'react-hook-form'

import { ApiError, type RegisterRequest, type RegisterResponse } from '@/shared/api'
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

const validationTranslationKeys: Readonly<Record<string, string>> = {
  'Name is required.': 'auth.register.validation.nameRequired',
  'Name is too long.': 'auth.register.validation.nameTooLong',
  'Email is required.': 'auth.register.validation.emailRequired',
  'Email is too long.': 'auth.register.validation.emailTooLong',
  'Enter a valid email address.': 'auth.register.validation.emailInvalid',
  'Password must contain at least 8 characters.': 'auth.register.validation.passwordMinimum',
  'Password must contain at most 128 characters.': 'auth.register.validation.passwordMaximum',
  'Passwords do not match.': 'auth.register.validation.passwordMismatch',
}

export interface RegisterFormProps {
  readonly onSuccess: (registration: RegisterResponse) => void
}

/**
 * Collects and validates the information required to create a password account.
 */
export function RegisterForm({ onSuccess }: RegisterFormProps) {
  const { t } = useTranslation()
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
      name: formData.name,
      email: formData.email,
      password: formData.password,
    }

    try {
      const registration = await registerWithPassword(request)
      onSuccess(registration)
    } catch (error) {
      setSubmissionError(registrationErrorMessage(error, t))
    }
  }

  return (
    <form className="space-y-5" noValidate onSubmit={handleSubmit(submitRegistration)}>
      {submissionError !== null ? (
        <Alert heading={t('auth.register.errors.heading')} variant="danger">
          {submissionError}
        </Alert>
      ) : null}

      <div className="space-y-2">
        <Label htmlFor="register-name">{t('auth.register.fields.name')}</Label>

        <Input
          {...register('name')}
          aria-describedby={errors.name ? 'register-name-error' : undefined}
          aria-invalid={errors.name ? true : undefined}
          autoComplete="name"
          disabled={isSubmitting}
          id="register-name"
          placeholder={t('auth.register.fields.namePlaceholder')}
        />

        {errors.name ? (
          <FieldMessage id="register-name-error" variant="error">
            {validationErrorMessage(errors.name.message, t)}
          </FieldMessage>
        ) : null}
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-email">{t('auth.register.fields.email')}</Label>

        <Input
          {...register('email')}
          aria-describedby={errors.email ? 'register-email-error' : undefined}
          aria-invalid={errors.email ? true : undefined}
          autoComplete="email"
          disabled={isSubmitting}
          id="register-email"
          inputMode="email"
          placeholder={t('auth.register.fields.emailPlaceholder')}
          type="email"
        />

        {errors.email ? (
          <FieldMessage id="register-email-error" variant="error">
            {validationErrorMessage(errors.email.message, t)}
          </FieldMessage>
        ) : null}
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-password">{t('auth.register.fields.password')}</Label>

        <Input
          {...register('password')}
          aria-describedby={errors.password ? 'register-password-error' : 'register-password-hint'}
          aria-invalid={errors.password ? true : undefined}
          autoComplete="new-password"
          disabled={isSubmitting}
          id="register-password"
          type="password"
        />

        {errors.password ? (
          <FieldMessage id="register-password-error" variant="error">
            {validationErrorMessage(errors.password.message, t)}
          </FieldMessage>
        ) : (
          <FieldMessage id="register-password-hint">
            {t('auth.register.fields.passwordHint')}
          </FieldMessage>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="register-confirm-password">
          {t('auth.register.fields.confirmPassword')}
        </Label>

        <Input
          {...register('confirmPassword')}
          aria-describedby={errors.confirmPassword ? 'register-confirm-password-error' : undefined}
          aria-invalid={errors.confirmPassword ? true : undefined}
          autoComplete="new-password"
          disabled={isSubmitting}
          id="register-confirm-password"
          type="password"
        />

        {errors.confirmPassword ? (
          <FieldMessage id="register-confirm-password-error" variant="error">
            {validationErrorMessage(errors.confirmPassword.message, t)}
          </FieldMessage>
        ) : null}
      </div>

      <Button
        className="w-full"
        isLoading={isSubmitting}
        loadingContent={t('auth.register.actions.creating')}
        type="submit"
      >
        {t('auth.register.actions.create')}
      </Button>
    </form>
  )
}

function validationErrorMessage(message: string | undefined, t: TFunction): string {
  if (message === undefined) {
    return t('auth.register.errors.invalidData')
  }

  const translationKey = validationTranslationKeys[message]

  return translationKey !== undefined ? t(translationKey) : message
}

function registrationErrorMessage(error: unknown, t: TFunction): string {
  if (
    error instanceof ApiError &&
    error.code === 'invalid_input' &&
    error.details.code === 'already_exists'
  ) {
    return t('auth.register.errors.accountExists')
  }

  if (error instanceof ApiError && error.status === null) {
    return t('auth.register.errors.network')
  }

  return t('auth.register.errors.invalidData')
}
