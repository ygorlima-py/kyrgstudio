import type { ComponentPropsWithRef } from 'react'

import { cn } from '@/shared/utils/class-names'

export type InputProps = ComponentPropsWithRef<'input'>

/**
 * Single-line text input with consistent validation and interaction states.
 */
export function Input({ className, type = 'text', ...inputProps }: InputProps) {
  return (
    <input
      className={cn(
        'h-11 w-full rounded-md border border-border-strong',
        'bg-surface px-3 text-body text-text shadow-sm',
        'placeholder:text-text-subtle',
        'transition-colors duration-(--duration-fast) ease-standard',
        'hover:border-text-subtle',
        'focus-visible:border-focus focus-visible:outline-none',
        'focus-visible:ring-3 focus-visible:ring-focus',
        'focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        'aria-invalid:border-danger aria-invalid:ring-danger',
        'disabled:cursor-not-allowed disabled:bg-surface-muted',
        'disabled:text-text-subtle disabled:opacity-70',
        'file:mr-3 file:border-0 file:bg-transparent file:text-label file:text-text',
        className,
      )}
      type={type}
      {...inputProps}
    />
  )
}
