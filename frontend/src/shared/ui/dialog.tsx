import type { ComponentPropsWithRef, HTMLAttributes } from 'react'

import * as DialogPrimitive from '@radix-ui/react-dialog'

import { i18n } from '@/shared/i18n/i18n'
import { cn } from '@/shared/utils/class-names'

export type DialogProps = ComponentPropsWithRef<typeof DialogPrimitive.Root>

/** Coordinates the controlled or uncontrolled dialog state. */
export function Dialog(dialogProps: DialogProps) {
  return <DialogPrimitive.Root {...dialogProps} />
}

export type DialogTriggerProps = ComponentPropsWithRef<typeof DialogPrimitive.Trigger>

/** Opens the nearest Dialog and supports Radix asChild composition. */
export function DialogTrigger(triggerProps: DialogTriggerProps) {
  return <DialogPrimitive.Trigger {...triggerProps} />
}

export type DialogCloseProps = ComponentPropsWithRef<typeof DialogPrimitive.Close>

/** Closes the nearest Dialog and supports Radix asChild composition. */
export function DialogClose(closeProps: DialogCloseProps) {
  return <DialogPrimitive.Close {...closeProps} />
}

export type DialogContentProps = ComponentPropsWithRef<typeof DialogPrimitive.Content>

/**
 * Modal surface rendered in a portal with focus trapping and an accessible
 * close control.
 */
export function DialogContent({ children, className, ...contentProps }: DialogContentProps) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Overlay
        className={cn(
          'fixed inset-0 z-50 bg-overlay',
          'transition-opacity duration-(--duration-normal) ease-standard',
          'data-[state=closed]:opacity-0 data-[state=open]:opacity-100',
        )}
      />
      <DialogPrimitive.Content
        className={cn(
          'fixed top-1/2 left-1/2 z-50 grid max-h-[calc(100dvh-2rem)]',
          'w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 -translate-y-1/2',
          'gap-6 overflow-y-auto rounded-lg border border-border',
          'bg-surface-raised p-6 text-text shadow-lg sm:p-8',
          'transition-[opacity,transform] duration-(--duration-normal) ease-standard',
          'data-[state=closed]:scale-95 data-[state=closed]:opacity-0',
          'data-[state=open]:scale-100 data-[state=open]:opacity-100',
          'focus:outline-none',
          className,
        )}
        {...contentProps}
      >
        {children}
        <DialogPrimitive.Close
          aria-label={i18n.t('shared.ui.dialog.close')}
          className={cn(
            'absolute top-4 right-4 inline-flex size-9 items-center justify-center',
            'rounded-md text-text-muted',
            'transition-colors duration-(--duration-fast) ease-standard',
            'hover:bg-surface-muted hover:text-text',
            'focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus',
            'disabled:pointer-events-none disabled:opacity-50',
          )}
        >
          <CloseIcon />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPrimitive.Portal>
  )
}

export type DialogTitleProps = ComponentPropsWithRef<typeof DialogPrimitive.Title>

/** Identifies the dialog for assistive technologies. */
export function DialogTitle({ className, ...titleProps }: DialogTitleProps) {
  return (
    <DialogPrimitive.Title
      className={cn('font-heading text-heading-3 text-text', className)}
      {...titleProps}
    />
  )
}

export type DialogDescriptionProps = ComponentPropsWithRef<typeof DialogPrimitive.Description>

/** Provides supporting context for the dialog purpose. */
export function DialogDescription({ className, ...descriptionProps }: DialogDescriptionProps) {
  return (
    <DialogPrimitive.Description
      className={cn('text-body-sm text-text-muted', className)}
      {...descriptionProps}
    />
  )
}

export type DialogHeaderProps = HTMLAttributes<HTMLDivElement>

/** Groups the dialog title and description. */
export function DialogHeader({ className, ...headerProps }: DialogHeaderProps) {
  return <div className={cn('grid gap-2 pr-10', className)} {...headerProps} />
}

export type DialogFooterProps = HTMLAttributes<HTMLDivElement>

/** Aligns dialog actions responsively. */
export function DialogFooter({ className, ...footerProps }: DialogFooterProps) {
  return (
    <div
      className={cn(
        'flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-end',
        className,
      )}
      {...footerProps}
    />
  )
}

function CloseIcon() {
  return (
    <svg aria-hidden="true" className="size-4" fill="none" viewBox="0 0 16 16">
      <path d="m4 4 8 8m0-8-8 8" stroke="currentColor" strokeLinecap="round" strokeWidth="1.75" />
    </svg>
  )
}
