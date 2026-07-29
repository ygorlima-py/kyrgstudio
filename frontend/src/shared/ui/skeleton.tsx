import type { HTMLAttributes } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const skeletonVariants = cva('animate-pulse bg-surface-muted', {
  variants: {
    variant: {
      text: 'h-4 rounded-sm',
      block: 'min-h-24 rounded-md',
      circle: 'aspect-square rounded-pill',
    },
  },
  defaultVariants: {
    variant: 'text',
  },
})

export interface SkeletonProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof skeletonVariants> {}

/**
 * Decorative loading placeholder hidden from assistive technologies.
 */
export function Skeleton({
  'aria-hidden': ariaHidden = true,
  className,
  variant,
  ...skeletonProps
}: SkeletonProps) {
  return (
    <div
      aria-hidden={ariaHidden}
      className={cn(skeletonVariants({ variant }), className)}
      {...skeletonProps}
    />
  )
}
