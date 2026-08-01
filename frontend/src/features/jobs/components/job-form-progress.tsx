import { cn } from '@/shared/utils/class-names'

import type {
  JobFormStep,
  JobFormStepId,
} from '../config/job-form-steps'

export interface JobFormProgressProps {
  readonly currentStepId: JobFormStepId
  readonly steps: readonly JobFormStep[]
}

/**
 * Shows the current position in the job creation flow.
 */
export function JobFormProgress({
  currentStepId,
  steps,
}: JobFormProgressProps) {
  const currentStepIndex = steps.findIndex(
    (step) => step.id === currentStepId,
  )

  const currentStep = steps[currentStepIndex]

  if (currentStep === undefined) {
    return null
  }

  return (
    <nav aria-label="Job creation progress">
      <div className="border-b border-border pb-4 sm:hidden">
        <p className="font-mono text-meta uppercase tracking-[0.12em] text-text-subtle">
          Step {currentStepIndex + 1} of {steps.length}
        </p>
        <p className="mt-1 text-label text-text">
          {currentStep.label}
        </p>
      </div>

      <ol
        className="hidden sm:grid"
        style={{
          gridTemplateColumns: `repeat(${steps.length}, minmax(0, 1fr))`,
        }}
      >
        {steps.map((step, index) => {
          const isCurrent = index === currentStepIndex
          const isCompleted = index < currentStepIndex

          return (
            <li
              aria-current={isCurrent ? 'step' : undefined}
              className={cn(
                'border-b-2 pb-3',
                isCurrent && 'border-action',
                isCompleted && 'border-text-muted',
                !isCurrent && !isCompleted && 'border-border',
              )}
              key={step.id}
            >
              <span
                className={cn(
                  'font-mono text-meta',
                  isCurrent && 'text-action',
                  isCompleted && 'text-text-muted',
                  !isCurrent && !isCompleted && 'text-text-subtle',
                )}
              >
                {String(index + 1).padStart(2, '0')}
              </span>

              <span
                className={cn(
                  'ml-2 text-body-sm font-medium',
                  isCurrent ? 'text-text' : 'text-text-muted',
                )}
              >
                {step.label}
              </span>
            </li>
          )
        })}
      </ol>
    </nav>
  )
}