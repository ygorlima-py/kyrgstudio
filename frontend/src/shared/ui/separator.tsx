import type { HTMLAttributes } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const separatorVariants = cva('shrink-0 bg-border', {
  variants: {
    orientation: {
      horizontal: 'h-px w-full',
      vertical: 'h-full min-h-4 w-px self-stretch',
    },
    emphasis: {
      default: 'bg-border',
      strong: 'bg-border-strong',
    },
  },
  defaultVariants: {
    orientation: 'horizontal',
    emphasis: 'default',
  },
})

export interface SeparatorProps
  extends HTMLAttributes<HTMLDivElement>, VariantProps<typeof separatorVariants> {
  /**
   * Removes separator semantics when the element is only visual decoration.
   */
  decorative?: boolean
}

/**
 * Divides related content either horizontally or vertically.
 */
export function Separator({
  className,
  decorative = false,
  emphasis,
  orientation,
  ...separatorProps
}: SeparatorProps) {
  const resolvedOrientation = orientation ?? 'horizontal'

  return (
    <div
      {...separatorProps}
      aria-hidden={decorative || undefined}
      aria-orientation={decorative ? undefined : resolvedOrientation}
      className={cn(separatorVariants({ emphasis, orientation: resolvedOrientation }), className)}
      role={decorative ? 'none' : 'separator'}
    />
  )
}
