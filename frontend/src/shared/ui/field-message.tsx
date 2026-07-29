import type { HTMLAttributes } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const fieldMessageVariants = cva('text-body-sm', {
  variants: {
    variant: {
      hint: 'text-text-muted',
      error: 'text-danger',
      success: 'text-success',
      warning: 'text-warning',
    },
  },
  defaultVariants: {
    variant: 'hint',
  },
})

export interface FieldMessageProps
  extends HTMLAttributes<HTMLParagraphElement>, VariantProps<typeof fieldMessageVariants> {}

/**
 * Supporting or validation message associated with a form control.
 */
export function FieldMessage({ className, role, variant, ...messageProps }: FieldMessageProps) {
  return (
    <p
      className={cn(fieldMessageVariants({ variant }), className)}
      role={role ?? (variant === 'error' ? 'alert' : undefined)}
      {...messageProps}
    />
  )
}
