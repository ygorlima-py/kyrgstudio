import type { HTMLAttributes, ReactNode } from 'react'

import { Alert } from '@/shared/ui/alert'
import { Stack } from '@/shared/ui/stack'
import { cn } from '@/shared/utils/class-names'

export interface ErrorStateProps extends Omit<
  HTMLAttributes<HTMLDivElement>,
  'children' | 'title'
> {
  /**
   * Short heading that identifies what failed.
   */
  title: ReactNode

  /**
   * User-facing explanation of the failure without exposing technical details.
   */
  description: ReactNode

  /**
   * Optional recovery action such as retrying or returning to another page.
   */
  action?: ReactNode
}

/**
 * Presents a controlled, accessible failure state for pages and sections.
 *
 * Technical messages, stack traces, provider responses, and internal error
 * details must not be passed to this component.
 */
export function ErrorState({
  action,
  className,
  description,
  title,
  ...stateProps
}: ErrorStateProps) {
  return (
    <Alert {...stateProps} className={cn('w-full', className)} heading={title} variant="danger">
      <Stack gap="md">
        <div>{description}</div>

        {action ? <div className="flex flex-wrap items-center gap-3">{action}</div> : null}
      </Stack>
    </Alert>
  )
}
