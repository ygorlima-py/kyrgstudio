import type { HTMLAttributes } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const badgeVariants = cva(
  'inline-flex w-fit items-center rounded-pill font-body whitespace-nowrap',
  {
    variants: {
      variant: {
        neutral: 'bg-surface-muted text-text-muted',
        action: 'bg-action-muted text-action',
        success: 'bg-success-muted text-success',
        warning: 'bg-warning-muted text-warning',
        danger: 'bg-danger-muted text-danger',
        processing: 'bg-processing-muted text-processing',
      },
      size: {
        sm: 'min-h-6 px-2.5 text-meta',
        md: 'min-h-7 px-3 text-label',
      },
    },
    defaultVariants: {
      variant: 'neutral',
      size: 'sm',
    },
  },
)

export interface BadgeProps
  extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

/**
 * Compact semantic label for statuses, categories, and metadata.
 */
export function Badge({ className, size, variant, ...badgeProps }: BadgeProps) {
  return <span className={cn(badgeVariants({ size, variant }), className)} {...badgeProps} />
}
