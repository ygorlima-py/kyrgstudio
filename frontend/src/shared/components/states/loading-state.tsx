import type { HTMLAttributes, ReactNode } from 'react'

import { Skeleton } from '@/shared/ui/skeleton'
import { Stack } from '@/shared/ui/stack'
import { cn } from '@/shared/utils/class-names'

export interface LoadingStateProps extends Omit<HTMLAttributes<HTMLDivElement>, 'children'> {
  /**
   * Accessible description announced while the content is loading.
   */
  label?: string

  /**
   * Optional placeholders matching the shape of the content being loaded.
   */
  children?: ReactNode
}

/**
 * Presents an accessible loading region with a reusable default skeleton.
 *
 * Consumers may provide custom skeletons through children when a page-specific
 * layout reduces visual movement after the real content is rendered.
 */
export function LoadingState({
  children,
  className,
  label = 'Loading content',
  ...stateProps
}: LoadingStateProps) {
  return (
    <div
      {...stateProps}
      aria-busy="true"
      aria-live="polite"
      className={cn('w-full', className)}
      role="status"
    >
      <span className="sr-only">{label}</span>
      {children ?? <DefaultLoadingSkeleton />}
    </div>
  )
}

function DefaultLoadingSkeleton() {
  return (
    <Stack aria-hidden="true" gap="lg">
      <Stack gap="sm">
        <Skeleton className="h-7 w-2/5 max-w-64" />
        <Skeleton className="w-full max-w-xl" />
        <Skeleton className="w-4/5 max-w-lg" />
      </Stack>
      <Skeleton className="min-h-40 w-full" variant="block" />
    </Stack>
  )
}
