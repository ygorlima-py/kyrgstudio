import type { JobStatus } from '../config/job-status'
import { cn } from '@/shared/utils/class-names'

const STATUS_STEPS = [
  {
    title: 'File received',
    description: 'Your reference is safely attached to this project.',
  },
  {
    title: 'Processing',
    description: 'We transcribe and examine the sales message.',
  },
  {
    title: 'Result ready',
    description: 'Your analysis or adapted script is available.',
  },
] as const

type TimelineStepState = 'complete' | 'current' | 'failed' | 'pending'

export interface JobStatusTimelineProps {
  readonly status: JobStatus
}

/** Display the durable product stages without exposing internal workflow nodes. */
export function JobStatusTimeline({ status }: JobStatusTimelineProps) {
  return (
    <div className="relative">
      <span
        aria-hidden="true"
        className="absolute top-4 right-[16.66%] left-[16.66%] hidden h-px bg-border md:block"
      />

      <ol aria-label="Project progress" className="relative grid md:grid-cols-3 md:gap-6">
        {STATUS_STEPS.map((step, index) => {
          const stepState = resolveStepState(status, index)

          return (
            <li
              aria-current={stepState === 'current' ? 'step' : undefined}
              className="relative flex gap-4 pb-7 last:pb-0 md:block md:pb-0 md:text-center"
              key={step.title}
            >
              {index < STATUS_STEPS.length - 1 ? (
                <span
                  aria-hidden="true"
                  className="absolute top-8 left-[15px] h-[calc(100%-1rem)] w-px bg-border md:hidden"
                />
              ) : null}

              <TimelineMarker state={stepState} />

              <div className="pt-1 md:mt-4 md:pt-0">
                <p
                  className={cn(
                    'text-label',
                    stepState === 'pending'
                      ? 'text-text-muted'
                      : stepState === 'failed'
                        ? 'text-danger'
                        : 'text-text',
                  )}
                >
                  {step.title}
                </p>

                <p className="mt-1 max-w-xs text-body-sm text-text-muted md:mx-auto">
                  {stepState === 'failed'
                    ? 'Processing stopped before this stage could finish.'
                    : step.description}
                </p>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

function resolveStepState(
  status: JobStatus,
  stepIndex: number,
): TimelineStepState {
  if (status === 'completed') {
    return 'complete'
  }

  if (status === 'failed') {
    if (stepIndex === 0) {
      return 'complete'
    }

    return stepIndex === 1 ? 'failed' : 'pending'
  }

  if (status === 'running') {
    if (stepIndex === 0) {
      return 'complete'
    }

    return stepIndex === 1 ? 'current' : 'pending'
  }

  return stepIndex === 0 ? 'complete' : 'pending'
}

function TimelineMarker({ state }: { readonly state: TimelineStepState }) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        'relative z-10 inline-flex size-8 shrink-0 items-center justify-center rounded-full border bg-surface',
        state === 'complete' && 'border-action bg-action text-text-inverse',
        state === 'current' && 'border-processing text-processing ring-4 ring-processing-muted',
        state === 'failed' && 'border-danger bg-danger text-text-inverse',
        state === 'pending' && 'border-border-strong text-text-subtle',
        'md:mx-auto',
      )}
    >
      {state === 'complete' ? <CheckIcon /> : null}
      {state === 'current' ? <CurrentIcon /> : null}
      {state === 'failed' ? <FailedIcon /> : null}
      {state === 'pending' ? <span className="size-2 rounded-full bg-border-strong" /> : null}
    </span>
  )
}

function CheckIcon() {
  return (
    <svg className="size-4" fill="none" viewBox="0 0 16 16">
      <path d="m3 8 3 3 7-7" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" />
    </svg>
  )
}

function CurrentIcon() {
  return <span className="size-2.5 animate-pulse rounded-full bg-processing" />
}

function FailedIcon() {
  return (
    <svg className="size-4" fill="none" viewBox="0 0 16 16">
      <path d="m5 5 6 6m0-6-6 6" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
    </svg>
  )
}
