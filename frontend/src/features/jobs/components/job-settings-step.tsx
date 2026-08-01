import { Controller, useFormContext } from 'react-hook-form'

import { Checkbox } from '@/shared/ui/checkbox'
import { FieldMessage } from '@/shared/ui/field-message'
import { Label } from '@/shared/ui/label'
import { Select } from '@/shared/ui/select'

import type { JobCreationFormInput } from '../schemas/job-creation-schema'

const LANGUAGE_OPTIONS = [
  {
    value: 'auto',
    label: 'Detect automatically',
  },
  {
    value: 'pt',
    label: 'Portuguese',
  },
  {
    value: 'en',
    label: 'English',
  },
  {
    value: 'es',
    label: 'Spanish',
  },
] as const

/**
 * Collects the transcription settings shared by analysis and adaptation jobs.
 *
 * Provider and model selection remain server-side defaults because they are
 * operational details that users do not need to configure in the MVP.
 */
export function JobSettingsStep() {
  const {
    control,
    formState: { errors },
  } = useFormContext<JobCreationFormInput>()

  const languageError =
    typeof errors.language?.message === 'string'
      ? errors.language.message
      : undefined

  return (
    <section
      aria-labelledby="job-settings-heading"
      className="space-y-8"
    >
      <div className="space-y-2">
        <h2
          className="font-heading text-heading-md text-text"
          id="job-settings-heading"
        >
          Configure the transcription
        </h2>

        <p className="max-w-2xl text-body text-text-muted">
          Tell us the original language and whether the transcript should
          receive an additional correction pass.
        </p>
      </div>

      <div className="max-w-xl space-y-2">
        <Label htmlFor="job-language">Original language</Label>

        <Controller
          control={control}
          name="language"
          render={({ field }) => (
            <Select
              aria-describedby="job-language-hint"
              aria-invalid={languageError ? true : undefined}
              id="job-language"
              onValueChange={(value) => {
                field.onChange(value === 'auto' ? '' : value)
              }}
              options={LANGUAGE_OPTIONS}
              value={field.value || 'auto'}
            />
          )}
        />

        {languageError ? (
          <FieldMessage variant="error">
            {languageError}
          </FieldMessage>
        ) : (
          <FieldMessage id="job-language-hint">
            Automatic detection works well when the recording uses one main
            language.
          </FieldMessage>
        )}
      </div>

      <Controller
        control={control}
        name="need_correction"
        render={({ field }) => (
          <div className="flex max-w-xl items-start gap-3">
            <Checkbox
              aria-describedby="transcription-correction-hint"
              checked={field.value ?? false}
              id="transcription-correction"
              onBlur={field.onBlur}
              onCheckedChange={(checked) => {
                field.onChange(checked === true)
              }}
            />

            <div className="space-y-1">
              <Label htmlFor="transcription-correction">
                Correct the transcript
              </Label>

              <FieldMessage id="transcription-correction-hint">
                Adds a correction step for recordings with transcription
                mistakes. Processing may take longer.
              </FieldMessage>
            </div>
          </div>
        )}
      />
    </section>
  )
}