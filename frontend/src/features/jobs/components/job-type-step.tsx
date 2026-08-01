import {
  useFormContext,
  useWatch,
} from 'react-hook-form'

import { FieldMessage } from '@/shared/ui/field-message'
import { cn } from '@/shared/utils/class-names'

import type {
  JobCreationFormInput,
  PipelineType,
} from '../schemas/job-creation-schema'

const PIPELINE_OPTIONS: readonly {
  value: PipelineType
  label: string
  description: string
}[] = [
  {
    value: 'copy_analysis',
    label: 'Analyze a copy',
    description:
      'Understand the structure, offer, persuasion, and strategy used in an existing sales message.',
  },
  {
    value: 'copy_adaptation',
    label: 'Adapt a copy',
    description:
      'Analyze a reference and create a new script grounded in your product, audience, and offer.',
  },
]

/**
 * Allows the user to select the pipeline used by the project.
 */
export function JobTypeStep() {
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
    <fieldset
      aria-describedby={
        errorMessage ? 'pipeline-type-error' : undefined
      }
    >
      <legend className="text-body-lg font-semibold text-text">
        What do you want to create?
      </legend>

      <p className="mt-2 max-w-2xl text-body text-text-muted">
        Choose whether you only want to study the reference or also
        transform its strategy into a new script.
      </p>

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
                isSelected
                  ? 'border-action shadow-sm'
                  : 'border-border',
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
                {option.label}
              </span>

              <span className="mt-2 block text-body-sm text-text-muted">
                {option.description}
              </span>
            </label>
          )
        })}
      </div>

      {errorMessage ? (
        <FieldMessage
          className="mt-3"
          id="pipeline-type-error"
          variant="error"
        >
          {errorMessage}
        </FieldMessage>
      ) : null}
    </fieldset>
  )
}