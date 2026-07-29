import type { HTMLAttributes } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const stackVariants = cva('flex flex-col', {
  variants: {
    gap: {
      none: 'gap-0',
      xs: 'gap-1',
      sm: 'gap-2',
      md: 'gap-4',
      lg: 'gap-6',
      xl: 'gap-8',
      '2xl': 'gap-12',
    },
    align: {
      stretch: 'items-stretch',
      start: 'items-start',
      center: 'items-center',
      end: 'items-end',
    },
  },
  defaultVariants: {
    gap: 'md',
    align: 'stretch',
  },
})

export interface StackProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof stackVariants> {}

/**
 * Arranges children vertically with a consistent gap and cross-axis alignment.
 */
export function Stack({ align, className, gap, ...stackProps }: StackProps) {
  return <div className={cn(stackVariants({ align, gap }), className)} {...stackProps} />
}
