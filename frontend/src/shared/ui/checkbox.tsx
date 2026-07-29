import type { ComponentPropsWithRef } from 'react'

import * as CheckboxPrimitive from '@radix-ui/react-checkbox'

import { cn } from '@/shared/utils/class-names'

export type CheckboxProps = ComponentPropsWithRef<typeof CheckboxPrimitive.Root>

/**
 * Keyboard-accessible checkbox supporting checked and indeterminate states.
 */
export function Checkbox({ className, ...checkboxProps }: CheckboxProps) {
  return (
    <CheckboxPrimitive.Root
      className={cn(
        'group inline-flex size-5 shrink-0 items-center justify-center rounded-sm',
        'border border-border-strong bg-surface text-text-inverse shadow-sm',
        'transition-colors duration-(--duration-fast) ease-standard',
        'hover:border-action',
        'focus-visible:outline-none focus-visible:ring-3',
        'focus-visible:ring-focus focus-visible:ring-offset-2',
        'focus-visible:ring-offset-background',
        'data-[state=checked]:border-action data-[state=checked]:bg-action',
        'data-[state=indeterminate]:border-action data-[state=indeterminate]:bg-action',
        'aria-invalid:border-danger aria-invalid:ring-3 aria-invalid:ring-danger',
        'disabled:cursor-not-allowed disabled:opacity-50',
        className,
      )}
      {...checkboxProps}
    >
      <CheckboxPrimitive.Indicator className="flex items-center justify-center">
        <CheckboxStateIcon />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  )
}

function CheckboxStateIcon() {
  return (
    <>
      <svg
        aria-hidden="true"
        className="hidden size-3.5 group-data-[state=checked]:block"
        fill="none"
        viewBox="0 0 16 16"
      >
        <path
          d="m3 8 3 3 7-7"
          stroke="currentColor"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="2"
        />
      </svg>
      <svg
        aria-hidden="true"
        className="hidden size-3.5 group-data-[state=indeterminate]:block"
        fill="none"
        viewBox="0 0 16 16"
      >
        <path d="M3 8h10" stroke="currentColor" strokeLinecap="round" strokeWidth="2" />
      </svg>
    </>
  )
}
