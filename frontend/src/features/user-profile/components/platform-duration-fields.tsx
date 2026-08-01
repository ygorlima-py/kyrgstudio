import { get, useFormContext } from 'react-hook-form'

import type { JobCreationFormInput } from '@/features/jobs/schemas/job-creation-schema'
import { FieldMessage } from '@/shared/ui/field-message'
import { Input } from '@/shared/ui/input'
import { Label } from '@/shared/ui/label'

import { ProfileTextField } from './profile-text-field'

/**
 * Defines where the adapted copy will be published and its intended duration.
 *
 * The duration is expressed in minutes, matching the backend contract.
 */
export function PlatformDurationFields() {
  const {
    formState: { errors },
    register,
  } = useFormContext<JobCreationFormInput>()

  const durationError: unknown = get(
    errors,
    'user_profile.desired_duration',
  )
  const durationErrorMessage = getErrorMessage(durationError)

  return (
    <section
      aria-labelledby="platform-duration-heading"
      className="space-y-5 border-t border-border pt-8"
    >
      <div className="space-y-1">
        <h3
          className="font-heading text-heading-sm text-text"
          id="platform-duration-heading"
        >
          Platform and duration
        </h3>

        <p className="text-body-sm text-text-muted">
          Define where the copy will be used and the approximate length of the
          final script.
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ProfileTextField
          description="Examples include Instagram, YouTube, a sales page, webinar, or paid advertisement."
          label="Where will this copy be used?"
          multiline={false}
          name="user_profile.platform"
          placeholder="Example: Instagram"
        />

        <div className="space-y-2">
          <Label htmlFor="user-profile-desired-duration">
            Desired duration in minutes
          </Label>

          <Input
            {...register('user_profile.desired_duration', {
              valueAsNumber: true,
            })}
            aria-describedby={
              durationErrorMessage
                ? 'desired-duration-error'
                : 'desired-duration-hint'
            }
            aria-invalid={
              durationErrorMessage ? true : undefined
            }
            id="user-profile-desired-duration"
            min="0.1"
            placeholder="Example: 2"
            step="0.1"
            type="number"
          />

          {durationErrorMessage ? (
            <FieldMessage
              id="desired-duration-error"
              variant="error"
            >
              {durationErrorMessage}
            </FieldMessage>
          ) : (
            <FieldMessage id="desired-duration-hint">
              Use decimal values when needed, such as 1.5 for one minute and
              thirty seconds.
            </FieldMessage>
          )}
        </div>
      </div>
    </section>
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