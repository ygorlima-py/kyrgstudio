import type { HTMLAttributes } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const containerVariants = cva('mx-auto w-full', {
  variants: {
    size: {
      content: 'max-w-content',
      reading: 'max-w-reading',
      form: 'max-w-form',
      full: 'max-w-none',
    },
    gutter: {
      none: 'px-0',
      sm: 'px-4',
      md: 'px-4 sm:px-6',
      lg: 'px-4 sm:px-6 lg:px-8',
    },
  },
  defaultVariants: {
    size: 'content',
    gutter: 'lg',
  },
})

export interface ContainerProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof containerVariants> {}

/**
 * Centers page content and applies consistent responsive horizontal gutters.
 */
export function Container({ className, gutter, size, ...containerProps }: ContainerProps) {
  return <div className={cn(containerVariants({ gutter, size }), className)} {...containerProps} />
}
