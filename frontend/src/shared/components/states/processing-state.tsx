import { useId, type HTMLAttributes, type ReactNode } from 'react'

import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'
import { Progress } from '@/shared/ui/progress'
import { Stack } from '@/shared/ui/stack'
import { cn } from '@/shared/utils/class-names'

export interface ProcessingStateProps extends Omit<
  HTMLAttributes<HTMLDivElement>,
  'children' | 'title'
> {
  /**
   * Main heading describing the operation currently being processed.
   */
  title: ReactNode

  /**
   * Optional supporting text explaining what is happening.
   */
  description?: ReactNode

  /**
   * Optional public status displayed above the heading.
   */
  statusLabel?: ReactNode

  /**
   * Accessible description for the progress indicator.
   */
  progressLabel: string

  /**
   * Current progress value. When omitted, progress is indeterminate.
   */
  progress?: number

  /**
   * Maximum progress value used to calculate completion percentage.
   */
  maxProgress?: number

  /**
   * Optional action such as canceling the operation or returning to another page.
   */
  action?: ReactNode
}

/**
 * Presents a long-running operation that has started but has not completed.
 *
 * Unlike LoadingState, this component represents persisted background work,
 * such as a queued or running pipeline job. It does not poll the API or manage
 * job state; it only renders values received from its parent.
 */
export function ProcessingState({
  action,
  className,
  description,
  maxProgress = 100,
  progress,
  progressLabel,
  statusLabel,
  title,
  ...stateProps
}: ProcessingStateProps) {
  const titleId = useId()
  const descriptionId = useId()

  return (
    <Card
      {...stateProps}
      aria-busy="true"
      aria-describedby={description ? descriptionId : undefined}
      aria-labelledby={titleId}
      className={cn('w-full', className)}
      padding="lg"
      role="region"
    >
      <Stack gap="lg">
        <Stack gap="sm">
          {statusLabel ? <Badge variant="processing">{statusLabel}</Badge> : null}

          <h2 className="font-heading text-heading-3 text-text" id={titleId}>
            {title}
          </h2>

          {description ? (
            <div className="max-w-reading text-body text-text-muted" id={descriptionId}>
              {description}
            </div>
          ) : null}
        </Stack>

        <Progress
          {...(progress === undefined ? {} : { value: progress })}
          label={progressLabel}
          max={maxProgress}
          variant="processing"
        />

        {action ? <div className="flex flex-wrap items-center gap-3">{action}</div> : null}
      </Stack>
    </Card>
  )
}
