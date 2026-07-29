import type { HTMLAttributes } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const inlineVariants = cva('flex flex-row', {
  variants: {
    gap: {
      none: 'gap-0',
      xs: 'gap-1',
      sm: 'gap-2',
      md: 'gap-4',
      lg: 'gap-6',
      xl: 'gap-8',
    },
    align: {
      stretch: 'items-stretch',
      start: 'items-start',
      center: 'items-center',
      end: 'items-end',
      baseline: 'items-baseline',
    },
    justify: {
      start: 'justify-start',
      center: 'justify-center',
      end: 'justify-end',
      between: 'justify-between',
      around: 'justify-around',
    },
    wrap: {
      wrap: 'flex-wrap',
      nowrap: 'flex-nowrap',
      reverse: 'flex-wrap-reverse',
    },
  },
  defaultVariants: {
    gap: 'md',
    align: 'center',
    justify: 'start',
    wrap: 'wrap',
  },
})

export interface InlineProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof inlineVariants> {}

/**
 * Arranges children horizontally with predictable wrapping and alignment.
 */
export function Inline({ align, className, gap, justify, wrap, ...inlineProps }: InlineProps) {
  return (
    <div
      className={cn(inlineVariants({ align, gap, justify, wrap }), className)}
      {...inlineProps}
    />
  )
}
