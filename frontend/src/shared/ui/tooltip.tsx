import type { ComponentPropsWithRef } from 'react'

import * as TooltipPrimitive from '@radix-ui/react-tooltip'

import { cn } from '@/shared/utils/class-names'

export type TooltipProviderProps = ComponentPropsWithRef<typeof TooltipPrimitive.Provider>

/**
 * Configures timing behavior shared by descendant tooltips.
 */
export function TooltipProvider({
  delayDuration = 300,
  skipDelayDuration = 200,
  ...providerProps
}: TooltipProviderProps) {
  return (
    <TooltipPrimitive.Provider
      delayDuration={delayDuration}
      skipDelayDuration={skipDelayDuration}
      {...providerProps}
    />
  )
}

export type TooltipProps = ComponentPropsWithRef<typeof TooltipPrimitive.Root>

/** Coordinates the controlled or uncontrolled tooltip state. */
export function Tooltip(tooltipProps: TooltipProps) {
  return <TooltipPrimitive.Root {...tooltipProps} />
}

export type TooltipTriggerProps = ComponentPropsWithRef<typeof TooltipPrimitive.Trigger>

/** Anchors a Tooltip and supports Radix asChild composition. */
export function TooltipTrigger(triggerProps: TooltipTriggerProps) {
  return <TooltipPrimitive.Trigger {...triggerProps} />
}

export type TooltipContentProps = ComponentPropsWithRef<typeof TooltipPrimitive.Content>

/**
 * Portalled supporting text displayed on pointer hover or keyboard focus.
 */
export function TooltipContent({
  className,
  collisionPadding = 8,
  sideOffset = 6,
  ...contentProps
}: TooltipContentProps) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        className={cn(
          'z-50 max-w-64 rounded-sm bg-text px-3 py-2',
          'text-body-sm text-text-inverse shadow-md',
          'transition-[opacity,transform] duration-(--duration-fast) ease-standard',
          'data-[state=closed]:scale-95 data-[state=closed]:opacity-0',
          'data-[state=instant-open]:scale-100 data-[state=instant-open]:opacity-100',
          'data-[state=delayed-open]:scale-100 data-[state=delayed-open]:opacity-100',
          className,
        )}
        collisionPadding={collisionPadding}
        sideOffset={sideOffset}
        {...contentProps}
      />
    </TooltipPrimitive.Portal>
  )
}
