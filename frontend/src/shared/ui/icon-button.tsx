import type { ReactNode } from 'react'

import { cva } from 'class-variance-authority'

import { Button, type ButtonProps } from '@/shared/ui/button'
import { cn } from '@/shared/utils/class-names'

const iconButtonSizeVariants = cva('shrink-0 p-0', {
  variants: {
    size: {
      sm: 'size-9',
      md: 'size-11',
      lg: 'size-12',
    },
  },
  defaultVariants: {
    size: 'md',
  },
})

const iconSizeVariants = cva('inline-flex shrink-0 items-center justify-center [&>svg]:size-full', {
  variants: {
    size: {
      sm: 'size-4',
      md: 'size-5',
      lg: 'size-5',
    },
  },
  defaultVariants: {
    size: 'md',
  },
})

export interface IconButtonProps extends Omit<
  ButtonProps,
  'aria-label' | 'children' | 'loadingContent'
> {
  /**
   * Accessible action name announced when the visual icon has no text.
   */
  'aria-label': string

  /**
   * Decorative icon representing the button action.
   */
  children: ReactNode
}

/**
 * Accessible square action button for controls represented only by an icon.
 */
export function IconButton({
  'aria-label': accessibleLabel,
  children,
  className,
  isLoading = false,
  size,
  ...buttonProps
}: IconButtonProps) {
  return (
    <Button
      {...buttonProps}
      aria-label={accessibleLabel}
      className={cn(iconButtonSizeVariants({ size }), className)}
      isLoading={isLoading}
      loadingContent={null}
      size={size}
    >
      <span aria-hidden="true" className={iconSizeVariants({ size })}>
        {children}
      </span>
    </Button>
  )
}
