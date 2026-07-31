import { useId, type HTMLAttributes, type ReactNode } from 'react'

import { Badge } from '@/shared/ui/badge'
import { Card } from '@/shared/ui/card'
import { Stack } from '@/shared/ui/stack'
import { cn } from '@/shared/utils/class-names'

export interface SuccessStateProps extends Omit<
  HTMLAttributes<HTMLDivElement>,
  'children' | 'title'
> {
  /**
   * Main heading describing the successfully completed operation.
   */
  title: ReactNode

  /**
   * Optional supporting text explaining the successful result.
   */
  description?: ReactNode

  /**
   * Optional public status displayed above the heading.
   */
  statusLabel?: ReactNode

  /**
   * Optional decorative icon. A confirmation icon is used by default.
   */
  icon?: ReactNode

  /**
   * Optional action such as viewing the result or starting another operation.
   */
  action?: ReactNode
}

/**
 * Presents an accessible confirmation after an operation completes successfully.
 *
 * This component only renders the completed state. It does not redirect,
 * update server data, download results, or execute another operation.
 */
export function SuccessState({
  action,
  className,
  description,
  icon = <SuccessIcon />,
  statusLabel,
  title,
  ...stateProps
}: SuccessStateProps) {
  const titleId = useId()
  const descriptionId = useId()

  return (
    <Card
      {...stateProps}
      aria-describedby={description ? descriptionId : undefined}
      aria-labelledby={titleId}
      aria-live="polite"
      className={cn('w-full', className)}
      padding="lg"
      role="status"
    >
      <Stack align="center" className="mx-auto max-w-reading text-center" gap="md">
        <div
          aria-hidden="true"
          className="flex size-12 items-center justify-center rounded-pill bg-success-muted text-success"
        >
          {icon}
        </div>

        <Stack align="center" gap="sm">
          {statusLabel ? <Badge variant="success">{statusLabel}</Badge> : null}

          <h2 className="font-heading text-heading-3 text-text" id={titleId}>
            {title}
          </h2>

          {description ? (
            <div className="max-w-xl text-body text-text-muted" id={descriptionId}>
              {description}
            </div>
          ) : null}
        </Stack>

        {action ? <div className="mt-2 flex flex-wrap justify-center gap-3">{action}</div> : null}
      </Stack>
    </Card>
  )
}

function SuccessIcon() {
  return (
    <svg aria-hidden="true" className="size-6" fill="none" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.75" />
      <path
        d="m8 12 2.5 2.5L16 9"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}
