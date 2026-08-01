import { get, useFormContext } from 'react-hook-form'

import type { JobCreationFormInput } from '@/features/jobs/schemas/job-creation-schema'
import { FieldMessage } from '@/shared/ui/field-message'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'
import { Textarea } from '@/shared/ui/textarea'

type UserProfileTextFieldName =
  | 'user_profile.product_or_solution'
  | 'user_profile.target_audience'
  | 'user_profile.core_problem'
  | 'user_profile.core_desire'
  | 'user_profile.main_promise'
  | 'user_profile.unique_mechanism'
  | 'user_profile.offer_details'
  | 'user_profile.call_to_action'
  | 'user_profile.tone'
  | 'user_profile.target_language'
  | 'user_profile.platform'

export interface ProfileTextFieldProps {
  name: UserProfileTextFieldName
  label: string
  description?: string
  placeholder?: string
  multiline?: boolean
}

/**
 * Renders a consistently labelled text field from the offer profile.
 */
export function ProfileTextField({
  description,
  label,
  multiline = true,
  name,
  placeholder,
}: ProfileTextFieldProps) {
  const {
    formState: { errors },
    register,
  } = useFormContext<JobCreationFormInput>()

  const fieldId = name.replace(/\./g, '-')
  const descriptionId = `${fieldId}-description`
  const errorId = `${fieldId}-error`
  const fieldError: unknown = get(errors, name)
  const errorMessage = getErrorMessage(fieldError)
  const registration = register(name)

  const accessibilityProps = {
    'aria-describedby': errorMessage
      ? errorId
      : description
        ? descriptionId
        : undefined,
    'aria-invalid': errorMessage ? true : undefined,
    id: fieldId,
    placeholder,
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={fieldId}>{label}</Label>

      {multiline ? (
        <Textarea
          {...registration}
          {...accessibilityProps}
          rows={4}
        />
      ) : (
        <Input
          {...registration}
          {...accessibilityProps}
        />
      )}

      {errorMessage ? (
        <FieldMessage id={errorId} variant="error">
          {errorMessage}
        </FieldMessage>
      ) : description ? (
        <FieldMessage id={descriptionId}>
          {description}
        </FieldMessage>
      ) : null}
    </div>
  )
}

function getErrorMessage(error: unknown): string | undefined {
  if (
    typeof error !== 'object' ||
    error === null ||
    !('message' in error)
  ) {
    return undefined
  }

  return typeof error.message === 'string'
    ? error.message
    : undefined
}