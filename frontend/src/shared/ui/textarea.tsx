import type { ComponentPropsWithRef } from 'react'

import { cn } from '@/shared/utils/class-names'

export type TextareaProps = ComponentPropsWithRef<'textarea'>

/**
 * Multi-line text input that grows vertically while preserving form styling.
 */
export function Textarea({ className, ...textareaProps }: TextareaProps) {
  return (
    <textarea
      className={cn(
        'min-h-32 w-full resize-y rounded-md border border-border-strong',
        'bg-surface px-3 py-2.5 text-body text-text shadow-sm',
        'placeholder:text-text-subtle',
        'transition-colors duration-(--duration-fast) ease-standard',
        'hover:border-text-subtle',
        'focus-visible:border-focus focus-visible:outline-none',
        'focus-visible:ring-3 focus-visible:ring-focus',
        'focus-visible:ring-offset-2 focus-visible:ring-offset-background',
        'aria-invalid:border-danger aria-invalid:ring-danger',
        'disabled:cursor-not-allowed disabled:resize-none',
        'disabled:bg-surface-muted disabled:text-text-subtle disabled:opacity-70',
        className,
      )}
      {...textareaProps}
    />
  )
}
