import type { ComponentPropsWithRef } from 'react'

import { cn } from '@/shared/utils/class-names'

export type LabelProps = ComponentPropsWithRef<'label'>

/**
 * Accessible label primitive for native and composed form controls.
 */
export function Label({ className, ...labelProps }: LabelProps) {
  return (
    <label
      className={cn(
        'inline-flex items-center gap-1.5 text-label text-text',
        'has-[:disabled]:cursor-not-allowed has-[:disabled]:opacity-60',
        className,
      )}
      {...labelProps}
    />
  )
}
