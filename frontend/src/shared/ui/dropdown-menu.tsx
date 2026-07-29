import type { ComponentPropsWithRef, HTMLAttributes } from 'react'

import * as DropdownMenuPrimitive from '@radix-ui/react-dropdown-menu'

import { cn } from '@/shared/utils/class-names'

export type DropdownMenuProps = ComponentPropsWithRef<typeof DropdownMenuPrimitive.Root>

/** Coordinates the controlled or uncontrolled dropdown menu state. */
export function DropdownMenu(menuProps: DropdownMenuProps) {
  return <DropdownMenuPrimitive.Root {...menuProps} />
}

export type DropdownMenuTriggerProps = ComponentPropsWithRef<typeof DropdownMenuPrimitive.Trigger>

/** Opens the nearest DropdownMenu and supports Radix asChild composition. */
export function DropdownMenuTrigger(triggerProps: DropdownMenuTriggerProps) {
  return <DropdownMenuPrimitive.Trigger {...triggerProps} />
}

export type DropdownMenuGroupProps = ComponentPropsWithRef<typeof DropdownMenuPrimitive.Group>

/** Groups related menu items for semantic navigation. */
export function DropdownMenuGroup(groupProps: DropdownMenuGroupProps) {
  return <DropdownMenuPrimitive.Group {...groupProps} />
}

export type DropdownMenuRadioGroupProps = ComponentPropsWithRef<
  typeof DropdownMenuPrimitive.RadioGroup
>

/** Coordinates the selected value among DropdownMenuRadioItem children. */
export function DropdownMenuRadioGroup(radioGroupProps: DropdownMenuRadioGroupProps) {
  return <DropdownMenuPrimitive.RadioGroup {...radioGroupProps} />
}

export type DropdownMenuSubProps = ComponentPropsWithRef<typeof DropdownMenuPrimitive.Sub>

/** Coordinates a nested dropdown submenu. */
export function DropdownMenuSub(subMenuProps: DropdownMenuSubProps) {
  return <DropdownMenuPrimitive.Sub {...subMenuProps} />
}

const contentClassName = cn(
  'z-50 min-w-48 overflow-hidden rounded-md border border-border',
  'bg-surface-raised p-1 text-text shadow-lg',
  'transition-[opacity,transform] duration-(--duration-fast) ease-standard',
  'data-[state=closed]:scale-95 data-[state=closed]:opacity-0',
  'data-[state=open]:scale-100 data-[state=open]:opacity-100',
)

export type DropdownMenuContentProps = ComponentPropsWithRef<typeof DropdownMenuPrimitive.Content>

/**
 * Portalled menu content with collision handling and keyboard navigation.
 */
export function DropdownMenuContent({
  className,
  collisionPadding = 8,
  sideOffset = 6,
  ...contentProps
}: DropdownMenuContentProps) {
  return (
    <DropdownMenuPrimitive.Portal>
      <DropdownMenuPrimitive.Content
        className={cn(contentClassName, className)}
        collisionPadding={collisionPadding}
        sideOffset={sideOffset}
        {...contentProps}
      />
    </DropdownMenuPrimitive.Portal>
  )
}

export interface DropdownMenuItemProps extends ComponentPropsWithRef<
  typeof DropdownMenuPrimitive.Item
> {
  inset?: boolean
}

/** Standard actionable menu item. */
export function DropdownMenuItem({
  className,
  inset = false,
  ...itemProps
}: DropdownMenuItemProps) {
  return (
    <DropdownMenuPrimitive.Item
      className={cn(menuItemClassName, inset && 'pl-9', className)}
      {...itemProps}
    />
  )
}

export interface DropdownMenuLabelProps extends ComponentPropsWithRef<
  typeof DropdownMenuPrimitive.Label
> {
  inset?: boolean
}

/** Non-interactive label for a group of menu items. */
export function DropdownMenuLabel({
  className,
  inset = false,
  ...labelProps
}: DropdownMenuLabelProps) {
  return (
    <DropdownMenuPrimitive.Label
      className={cn('px-3 py-2 text-label text-text-muted', inset && 'pl-9', className)}
      {...labelProps}
    />
  )
}

export type DropdownMenuCheckboxItemProps = ComponentPropsWithRef<
  typeof DropdownMenuPrimitive.CheckboxItem
>

/** Menu item that exposes a checked or indeterminate state. */
export function DropdownMenuCheckboxItem({
  children,
  className,
  ...itemProps
}: DropdownMenuCheckboxItemProps) {
  return (
    <DropdownMenuPrimitive.CheckboxItem
      className={cn(menuItemClassName, 'pl-9', className)}
      {...itemProps}
    >
      <DropdownMenuPrimitive.ItemIndicator className="absolute left-3 inline-flex size-4 items-center justify-center text-action">
        <CheckIcon />
      </DropdownMenuPrimitive.ItemIndicator>
      {children}
    </DropdownMenuPrimitive.CheckboxItem>
  )
}

export type DropdownMenuRadioItemProps = ComponentPropsWithRef<
  typeof DropdownMenuPrimitive.RadioItem
>

/** Selectable menu item used inside DropdownMenuRadioGroup. */
export function DropdownMenuRadioItem({
  children,
  className,
  ...itemProps
}: DropdownMenuRadioItemProps) {
  return (
    <DropdownMenuPrimitive.RadioItem
      className={cn(menuItemClassName, 'pl-9', className)}
      {...itemProps}
    >
      <DropdownMenuPrimitive.ItemIndicator className="absolute left-3 inline-flex size-4 items-center justify-center text-action">
        <RadioIcon />
      </DropdownMenuPrimitive.ItemIndicator>
      {children}
    </DropdownMenuPrimitive.RadioItem>
  )
}

export type DropdownMenuSeparatorProps = ComponentPropsWithRef<
  typeof DropdownMenuPrimitive.Separator
>

/** Visual divider between menu groups. */
export function DropdownMenuSeparator({
  className,
  ...separatorProps
}: DropdownMenuSeparatorProps) {
  return (
    <DropdownMenuPrimitive.Separator
      className={cn('-mx-1 my-1 h-px bg-border', className)}
      {...separatorProps}
    />
  )
}

export interface DropdownMenuSubTriggerProps extends ComponentPropsWithRef<
  typeof DropdownMenuPrimitive.SubTrigger
> {
  inset?: boolean
}

/** Opens a nested submenu. */
export function DropdownMenuSubTrigger({
  children,
  className,
  inset = false,
  ...triggerProps
}: DropdownMenuSubTriggerProps) {
  return (
    <DropdownMenuPrimitive.SubTrigger
      className={cn(menuItemClassName, inset && 'pl-9', className)}
      {...triggerProps}
    >
      {children}
      <ChevronRightIcon />
    </DropdownMenuPrimitive.SubTrigger>
  )
}

export type DropdownMenuSubContentProps = ComponentPropsWithRef<
  typeof DropdownMenuPrimitive.SubContent
>

/** Nested menu surface positioned by Radix relative to its parent item. */
export function DropdownMenuSubContent({
  className,
  ...contentProps
}: DropdownMenuSubContentProps) {
  return (
    <DropdownMenuPrimitive.SubContent
      className={cn(contentClassName, className)}
      {...contentProps}
    />
  )
}

export type DropdownMenuShortcutProps = HTMLAttributes<HTMLSpanElement>

/** Right-aligned keyboard shortcut or supporting metadata. */
export function DropdownMenuShortcut({ className, ...shortcutProps }: DropdownMenuShortcutProps) {
  return (
    <span
      className={cn('ml-auto pl-4 font-mono text-meta text-text-subtle', className)}
      {...shortcutProps}
    />
  )
}

const menuItemClassName = cn(
  'relative flex min-h-10 cursor-default select-none items-center gap-2',
  'rounded-sm px-3 py-2 text-body-sm outline-none',
  'transition-colors duration-(--duration-fast) ease-standard',
  'data-[highlighted]:bg-action-muted data-[highlighted]:text-text',
  'data-[disabled]:pointer-events-none data-[disabled]:opacity-45',
)

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

function RadioIcon() {
  return (
    <svg aria-hidden="true" className="size-3" fill="currentColor" viewBox="0 0 12 12">
      <circle cx="6" cy="6" r="3" />
    </svg>
  )
}

function ChevronRightIcon() {
  return (
    <svg aria-hidden="true" className="ml-auto size-4" fill="none" viewBox="0 0 16 16">
      <path
        d="m6 3 5 5-5 5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}
