import type { HTMLAttributes } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const cardVariants = cva('rounded-lg border text-text', {
  variants: {
    variant: {
      default: 'border-border bg-surface',
      muted: 'border-border bg-surface-muted',
      elevated: 'border-border bg-surface-raised shadow-md',
    },
    padding: {
      none: 'p-0',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    },
  },
  defaultVariants: {
    variant: 'default',
    padding: 'md',
  },
})

export interface CardProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof cardVariants> {}

/**
 * Surface primitive for grouping related content and actions.
 */
export function Card({ className, padding, variant, ...cardProps }: CardProps) {
  return <div className={cn(cardVariants({ padding, variant }), className)} {...cardProps} />
}
