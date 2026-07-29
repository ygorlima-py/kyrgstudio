import type { ComponentPropsWithRef } from 'react'

import * as TabsPrimitive from '@radix-ui/react-tabs'

import { cn } from '@/shared/utils/class-names'

export type TabsProps = ComponentPropsWithRef<typeof TabsPrimitive.Root>

/** Coordinates tab selection in controlled or uncontrolled mode. */
export function Tabs({ className, ...tabsProps }: TabsProps) {
  return <TabsPrimitive.Root className={cn('w-full', className)} {...tabsProps} />
}

export type TabsListProps = ComponentPropsWithRef<typeof TabsPrimitive.List>

/** Keyboard-navigable collection of tab triggers. */
export function TabsList({ className, ...listProps }: TabsListProps) {
  return (
    <TabsPrimitive.List
      className={cn(
        'inline-flex min-h-11 max-w-full items-center gap-1 overflow-x-auto',
        'rounded-md bg-surface-muted p-1 text-text-muted',
        className,
      )}
      {...listProps}
    />
  )
}

export type TabsTriggerProps = ComponentPropsWithRef<typeof TabsPrimitive.Trigger>

/** Activates the tab panel sharing the same value. */
export function TabsTrigger({ className, ...triggerProps }: TabsTriggerProps) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        'inline-flex min-h-9 shrink-0 items-center justify-center rounded-sm',
        'px-3 text-label whitespace-nowrap',
        'transition-colors duration-(--duration-fast) ease-standard',
        'hover:text-text',
        'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus',
        'data-[state=active]:bg-surface-raised data-[state=active]:text-text',
        'data-[state=active]:shadow-sm',
        'disabled:pointer-events-none disabled:opacity-50',
        className,
      )}
      {...triggerProps}
    />
  )
}

export type TabsContentProps = ComponentPropsWithRef<typeof TabsPrimitive.Content>

/** Content panel associated with a TabsTrigger value. */
export function TabsContent({ className, ...contentProps }: TabsContentProps) {
  return (
    <TabsPrimitive.Content
      className={cn(
        'mt-4 text-text',
        'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus',
        className,
      )}
      {...contentProps}
    />
  )
}
