import type { ButtonHTMLAttributes, ReactNode } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center rounded-md font-body',
    'whitespace-nowrap select-none',
    'transition-colors duration-(--duration-fast) ease-standard',
    'focus-visible:outline-none focus-visible:ring-3',
    'focus-visible:ring-focus focus-visible:ring-offset-2',
    'focus-visible:ring-offset-background',
    'disabled:pointer-events-none disabled:cursor-not-allowed',
    'disabled:opacity-50',
  ],
  {
    variants: {
      variant: {
        primary: [
          'bg-action text-white-inverse shadow-sm',
          'hover:bg-action-hover active:bg-action-active',
        ],
        secondary: [
          'border border-border-strong bg-surface text-text shadow-sm',
          'hover:bg-surface-muted active:bg-action-muted',
        ],
        danger: ['bg-danger text-text-inverse shadow-sm', 'hover:opacity-90 active:opacity-80'],
        ghost: ['text-text', 'hover:bg-surface-muted active:bg-action-muted'],
      },
      size: {
        sm: 'h-9 gap-2 px-3 text-body-sm',
        md: 'h-11 gap-2.5 px-4 text-label',
        lg: 'h-12 gap-3 px-6 text-body',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'md',
    },
  },
)

export interface ButtonProps
  extends ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {
  /**
   * Disables interaction and communicates that the button action is running.
   */
  isLoading?: boolean

  /**
   * Optional content displayed while the button action is running.
   */
  loadingContent?: ReactNode
}

/**
 * Primary action primitive shared by forms, dialogs, and application pages.
 */
export function Button({
  children,
  className,
  disabled = false,
  isLoading = false,
  loadingContent,
  size,
  type = 'button',
  variant,
  ...buttonProps
}: ButtonProps) {
  const displayedContent = isLoading && loadingContent !== undefined ? loadingContent : children

  return (
    <button
      {...buttonProps}
      aria-busy={isLoading || undefined}
      className={cn(buttonVariants({ variant, size }), className)}
      data-loading={isLoading || undefined}
      disabled={disabled || isLoading}
      type={type}
    >
      {isLoading ? <LoadingIndicator /> : null}
      {displayedContent}
    </button>
  )
}

function LoadingIndicator() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 shrink-0 animate-spin"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="3" />
      <path
        className="opacity-75"
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="3"
      />
    </svg>
  )
}
