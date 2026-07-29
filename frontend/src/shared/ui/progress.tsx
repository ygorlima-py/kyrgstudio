import type { HTMLAttributes } from 'react'

import { cva, type VariantProps } from 'class-variance-authority'

import { cn } from '@/shared/utils/class-names'

const progressIndicatorVariants = cva(
  'h-full rounded-pill transition-[width] duration-(--duration-normal) ease-standard',
  {
    variants: {
      variant: {
        action: 'bg-action',
        processing: 'bg-processing',
        success: 'bg-success',
        danger: 'bg-danger',
      },
    },
    defaultVariants: {
      variant: 'processing',
    },
  },
)

export interface ProgressProps
  extends
    Omit<HTMLAttributes<HTMLDivElement>, 'children'>,
    VariantProps<typeof progressIndicatorVariants> {
  /**
   * Accessible description of the operation represented by the progress bar.
   */
  label: string

  /**
   * Current progress. Omit it to render an indeterminate state.
   */
  value?: number

  /**
   * Maximum progress value. Invalid values safely fall back to 100.
   */
  max?: number
}

/**
 * Accessible determinate or indeterminate progress indicator.
 */
export function Progress({
  className,
  label,
  max = 100,
  value,
  variant,
  ...progressProps
}: ProgressProps) {
  const normalizedMax = normalizeMaximum(max)
  const normalizedValue = normalizeValue(value, normalizedMax)
  const percentage =
    normalizedValue === undefined ? undefined : (normalizedValue / normalizedMax) * 100

  const determinateAriaProps =
    normalizedValue === undefined ? {} : { 'aria-valuenow': normalizedValue }

  return (
    <div
      {...progressProps}
      {...determinateAriaProps}
      aria-label={label}
      aria-valuemax={normalizedMax}
      aria-valuemin={0}
      className={cn('h-2 w-full overflow-hidden rounded-pill bg-surface-muted', className)}
      data-state={normalizedValue === undefined ? 'indeterminate' : 'determinate'}
      role="progressbar"
    >
      <div
        className={cn(
          progressIndicatorVariants({ variant }),
          normalizedValue === undefined ? 'w-1/3 animate-pulse' : undefined,
        )}
        style={percentage === undefined ? undefined : { width: `${percentage}%` }}
      />
    </div>
  )
}

function normalizeMaximum(maximum: number): number {
  return Number.isFinite(maximum) && maximum > 0 ? maximum : 100
}

function normalizeValue(value: number | undefined, maximum: number): number | undefined {
  if (value === undefined) {
    return undefined
  }

  if (!Number.isFinite(value)) {
    return 0
  }

  return Math.min(Math.max(value, 0), maximum)
}
