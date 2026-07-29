import type { ComponentPropsWithoutRef, ReactNode } from 'react'

import * as SelectPrimitive from '@radix-ui/react-select'

import { cn } from '@/shared/utils/class-names'

export interface SelectOption {
  value: string
  label: ReactNode
  disabled?: boolean
}

type SelectRootProps = ComponentPropsWithoutRef<typeof SelectPrimitive.Root>
type SelectTriggerProps = ComponentPropsWithoutRef<typeof SelectPrimitive.Trigger>

export interface SelectProps extends Omit<SelectRootProps, 'children'> {
  options: readonly SelectOption[]
  placeholder?: string
  className?: string
  id?: string
  'aria-label'?: SelectTriggerProps['aria-label']
  'aria-labelledby'?: SelectTriggerProps['aria-labelledby']
  'aria-describedby'?: SelectTriggerProps['aria-describedby']
  'aria-invalid'?: SelectTriggerProps['aria-invalid']
}

/**
 * Accessible single-value select with keyboard navigation and portal content.
 */
export function Select({
  'aria-describedby': ariaDescribedBy,
  'aria-invalid': ariaInvalid,
  'aria-label': ariaLabel,
  'aria-labelledby': ariaLabelledBy,
  className,
  id,
  options,
  placeholder = 'Select an option',
  ...selectRootProps
}: SelectProps) {
  return (
    <SelectPrimitive.Root {...selectRootProps}>
      <SelectPrimitive.Trigger
        aria-describedby={ariaDescribedBy}
        aria-invalid={ariaInvalid}
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledBy}
        className={cn(
          'flex h-11 w-full items-center justify-between gap-3 rounded-md',
          'border border-border-strong bg-surface px-3 text-body text-text shadow-sm',
          'transition-colors duration-(--duration-fast) ease-standard',
          'hover:border-text-subtle',
          'focus-visible:border-focus focus-visible:outline-none',
          'focus-visible:ring-3 focus-visible:ring-focus',
          'focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          'data-[placeholder]:text-text-subtle',
          'aria-invalid:border-danger aria-invalid:ring-danger',
          'disabled:cursor-not-allowed disabled:bg-surface-muted',
          'disabled:text-text-subtle disabled:opacity-70',
          className,
        )}
        id={id}
      >
        <SelectPrimitive.Value placeholder={placeholder} />
        <SelectPrimitive.Icon aria-hidden="true" className="shrink-0 text-text-muted">
          <ChevronDownIcon />
        </SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>

      <SelectPrimitive.Portal>
        <SelectPrimitive.Content
          className={cn(
            'z-50 max-h-(--radix-select-content-available-height)',
            'min-w-(--radix-select-trigger-width) overflow-hidden rounded-md',
            'border border-border bg-surface-raised text-text shadow-lg',
            'data-[state=closed]:opacity-0 data-[state=open]:opacity-100',
            'transition-opacity duration-(--duration-fast) ease-standard',
          )}
          collisionPadding={8}
          position="popper"
          sideOffset={6}
        >
          <SelectPrimitive.Viewport className="p-1">
            {options.map((option) => (
              <SelectPrimitive.Item
                className={cn(
                  'relative flex min-h-10 cursor-default select-none items-center',
                  'rounded-sm py-2 pr-3 pl-9 text-body-sm outline-none',
                  'data-[highlighted]:bg-action-muted data-[highlighted]:text-text',
                  'data-[disabled]:pointer-events-none data-[disabled]:opacity-45',
                )}
                disabled={option.disabled ?? false}
                key={option.value}
                value={option.value}
              >
                <SelectPrimitive.ItemIndicator className="absolute left-3 inline-flex size-4 items-center justify-center text-action">
                  <CheckIcon />
                </SelectPrimitive.ItemIndicator>
                <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  )
}

function ChevronDownIcon() {
  return (
    <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 16 16">
      <path
        d="m4 6 4 4 4-4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 16 16">
      <path
        d="m3 8 3 3 7-7"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}
