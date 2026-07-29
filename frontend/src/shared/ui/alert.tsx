import type { HTMLAttributes, ReactNode } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const alertVariants = cva('rounded-md border px-4 py-3 text-body-sm', {
  variants: {
    variant: {
      info: 'border-processing bg-processing-muted text-processing',
      success: 'border-success bg-success-muted text-success',
      warning: 'border-warning bg-warning-muted text-warning',
      danger: 'border-danger bg-danger-muted text-danger',
    },
  },
  defaultVariants: {
    variant: 'info',
  },
})

export interface AlertProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof alertVariants> {
  heading?: ReactNode
}

/**
 * Semantic notice for important contextual or validation feedback.
 */
export function Alert({ children, className, heading, role, variant, ...alertProps }: AlertProps) {
  return (
    <div
      className={cn(alertVariants({ variant }), className)}
      role={role ?? (variant === 'danger' ? 'alert' : undefined)}
      {...alertProps}
    >
      {heading ? <p className="text-label">{heading}</p> : null}
      {children ? <div className={cn(heading ? 'mt-1' : undefined)}>{children}</div> : null}
    </div>
  )
}
