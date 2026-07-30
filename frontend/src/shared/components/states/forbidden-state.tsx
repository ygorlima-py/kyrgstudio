import type { ReactNode } from 'react'

import {
  EmptyState,
  type EmptyStateProps,
} from '@/shared/components/states/empty-state'

export interface ForbiddenStateProps extends Omit<EmptyStateProps, 'icon'> {
  /**
   * Optional decorative icon. A restricted-access icon is used by default.
   */
  icon?: ReactNode
}

/**
 * Presents a state indicating that the authenticated user does not have
 * permission to access the requested resource or operation.
 *
 * This component only renders public information. It must not expose internal
 * authorization rules, ownership details, roles, or permission identifiers.
 */
export function ForbiddenState({
  icon = <RestrictedAccessIcon />,
  ...emptyStateProps
}: ForbiddenStateProps) {
  return <EmptyState icon={icon} {...emptyStateProps} />
}

function RestrictedAccessIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-6"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M12 3 5 6v5c0 4.8 2.9 8.2 7 10 4.1-1.8 7-5.2 7-10V6l-7-3Z"
        stroke="currentColor"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
      <path
        d="m9 9 6 6m0-6-6 6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}