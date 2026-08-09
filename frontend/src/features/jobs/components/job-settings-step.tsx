import { useTranslation } from 'react-i18next'
import { Controller, useFormContext } from 'react-hook-form'

import { Checkbox } from '@/shared/ui/checkbox'
import { FieldMessage } from '@/shared/ui/field-message'
import { Label } from '@/shared/ui/label'
import { Select } from '@/shared/ui/select'

import type { JobCreationFormInput } from '../schemas/job-creation-schema'

const LANGUAGE_OPTIONS = [
  {
    value: 'auto',
    labelKey: 'newJob.settings.language.options.auto',
  },
  {
    value: 'pt',
    labelKey: 'newJob.settings.language.options.pt',
  },
  {
    value: 'en',
    labelKey: 'newJob.settings.language.options.en',
  },
  {
    value: 'es',
    labelKey: 'newJob.settings.language.options.es',
  },
] as const

/**
 * Collects the transcription settings shared by analysis and adaptation jobs.
 *
 * Provider and model selection remain server-side defaults because they are
 * operational details that users do not need to configure in the MVP.
 */
export function JobSettingsStep() {
  const { t } = useTranslation()
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
          {t('newJob.settings.title')}
        </h2>

        <p className="max-w-2xl text-body text-text-muted">
          {t('newJob.settings.description')}
        </p>
      </div>

      <div className="max-w-xl space-y-2">
        <Label htmlFor="job-language">
          {t('newJob.settings.language.label')}
        </Label>

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
              options={LANGUAGE_OPTIONS.map((option) => ({
                value: option.value,
                label: t(option.labelKey),
              }))}
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
            {t('newJob.settings.language.hint')}
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
                {t('newJob.settings.correction.label')}
              </Label>

              <FieldMessage id="transcription-correction-hint">
                {t('newJob.settings.correction.hint')}
              </FieldMessage>
            </div>
          </div>
        )}
      />
    </section>
  )
}
