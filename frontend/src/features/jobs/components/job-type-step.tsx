import { useFormContext, useWatch } from 'react-hook-form'
import { useTranslation } from 'react-i18next'

import { FieldMessage } from '@/shared/ui/field-message'
import { cn } from '@/shared/utils/class-names'

import type { JobCreationFormInput, PipelineType } from '../schemas/job-creation-schema'

const PIPELINE_OPTIONS: readonly {
  value: PipelineType
  labelKey: string
  descriptionKey: string
}[] = [
  {
    value: 'copy_analysis',
    labelKey: 'newJob.pipeline.options.analysis.label',
    descriptionKey: 'newJob.pipeline.options.analysis.description',
  },
  {
    value: 'copy_adaptation',
    labelKey: 'newJob.pipeline.options.adaptation.label',
    descriptionKey: 'newJob.pipeline.options.adaptation.description',
  },
]

/**
 * Allows the user to select the pipeline used by the project.
 */
export function JobTypeStep() {
  const { t } = useTranslation()
  const {
    control,
    formState: { errors },
    register,
  } = useFormContext<JobCreationFormInput>()

  const selectedPipeline = useWatch({
    control,
    name: 'pipeline_type',
  })

  const errorMessage = errors.pipeline_type?.message

  return (
    <fieldset aria-describedby={errorMessage ? 'pipeline-type-error' : undefined}>
      <legend className="text-body-lg font-semibold text-text">{t('newJob.pipeline.title')}</legend>

      <p className="mt-2 max-w-2xl text-body text-text-muted">{t('newJob.pipeline.description')}</p>

      <div className="mt-6 grid gap-4 md:grid-cols-2">
        {PIPELINE_OPTIONS.map((option) => {
          const isSelected = selectedPipeline === option.value

          return (
            <label
              className={cn(
                'cursor-pointer rounded-lg border bg-surface p-5',
                'transition-[border-color,box-shadow]',
                'hover:border-border-strong',
                'focus-within:ring-3 focus-within:ring-focus',
                isSelected ? 'border-action shadow-sm' : 'border-border',
              )}
              key={option.value}
            >
              <input
                {...register('pipeline_type')}
                className="sr-only"
                type="radio"
                value={option.value}
              />

              <span className="block text-body-lg font-semibold text-text">
                {t(option.labelKey)}
              </span>

              <span className="mt-2 block text-body-sm text-text-muted">
                {t(option.descriptionKey)}
              </span>
            </label>
          )
        })}
      </div>

      {errorMessage ? (
        <FieldMessage className="mt-3" id="pipeline-type-error" variant="error">
          {errorMessage}
        </FieldMessage>
      ) : null}
    </fieldset>
  )
}
