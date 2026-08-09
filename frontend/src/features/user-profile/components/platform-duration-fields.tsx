import { useTranslation } from 'react-i18next'
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
  const { t } = useTranslation()
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
          {t('userProfile.platformDuration.title')}
        </h3>

        <p className="text-body-sm text-text-muted">
          {t('userProfile.platformDuration.description')}
        </p>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <ProfileTextField
          description={t('userProfile.platformDuration.platform.description')}
          label={t('userProfile.platformDuration.platform.label')}
          multiline={false}
          name="user_profile.platform"
          placeholder={t('userProfile.platformDuration.platform.placeholder')}
        />

        <div className="space-y-2">
          <Label htmlFor="user-profile-desired-duration">
            {t('userProfile.platformDuration.duration.label')}
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
            placeholder={t('userProfile.platformDuration.duration.placeholder')}
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
              {t('userProfile.platformDuration.duration.hint')}
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
