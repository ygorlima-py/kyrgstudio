import type { ReactNode } from 'react'

import {
  EmptyState,
  type EmptyStateProps,
} from '@/shared/components/states/empty-state'

export interface UnauthorizedStateProps extends Omit<EmptyStateProps, 'icon'> {
  /**
   * Optional decorative icon. An authentication icon is used by default.
   */
  icon?: ReactNode
}

/**
 * Presents a state indicating that authentication is required.
 *
 * This component only renders the public message and action. It does not
 * redirect, read tokens, open sessions, or execute authentication logic.
 */
export function UnauthorizedState({
  icon = <AuthenticationRequiredIcon />,
  ...emptyStateProps
}: UnauthorizedStateProps) {
  return <EmptyState icon={icon} {...emptyStateProps} />
}

function AuthenticationRequiredIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-6"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M7 10V8a5 5 0 0 1 10 0v2"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
      <rect
        height="10"
        rx="2"
        stroke="currentColor"
        strokeWidth="1.75"
        width="16"
        x="4"
        y="10"
      />
      <path
        d="M12 14v2"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}