import { useId, type HTMLAttributes, type ReactNode } from 'react'

import { Card } from '@/shared/ui/card'
import { Stack } from '@/shared/ui/stack'
import { cn } from '@/shared/utils/class-names'

export interface EmptyStateProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  /**
   * Main message explaining why the section has no content.
   */
  title: ReactNode

  /**
   * Optional supporting text that helps the user understand the empty state.
   */
  description?: ReactNode

  /**
   * Optional decorative illustration or icon displayed above the title.
   */
  icon?: ReactNode

  /**
   * Optional action such as a button or link that helps the user continue.
   */
  action?: ReactNode
}

/**
 * Presents an accessible empty state for collections, searches, and resources
 * that currently contain no data.
 */
export function EmptyState({
  action,
  className,
  description,
  icon,
  title,
  ...stateProps
}: EmptyStateProps) {
  const titleId = useId()
  const descriptionId = useId()

  return (
    <Card
      {...stateProps}
      aria-describedby={description ? descriptionId : undefined}
      aria-labelledby={titleId}
      className={cn('w-full', className)}
      padding="lg"
      role="region"
      variant="muted"
    >
      <Stack align="center" className="mx-auto max-w-reading text-center" gap="md">
        {icon ? (
          <div
            aria-hidden="true"
            className="flex size-12 items-center justify-center rounded-pill bg-action-muted text-action"
          >
            {icon}
          </div>
        ) : null}

        <Stack align="center" gap="sm">
          <h2 className="font-heading text-heading-3 text-text" id={titleId}>
            {title}
          </h2>

          {description ? (
            <div className="max-w-xl text-body text-text-muted" id={descriptionId}>
              {description}
            </div>
          ) : null}
        </Stack>

        {action ? <div className="mt-2">{action}</div> : null}
      </Stack>
    </Card>
  )
}