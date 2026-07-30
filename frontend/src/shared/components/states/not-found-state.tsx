import type { ReactNode } from 'react'

import {
  EmptyState,
  type EmptyStateProps,
} from '@/shared/components/states/empty-state'

export interface NotFoundStateProps extends Omit<EmptyStateProps, 'icon'> {
  /**
   * Optional decorative icon. A missing-resource icon is used by default.
   */
  icon?: ReactNode
}

/**
 * Presents an accessible state when a requested page or resource cannot be
 * found or is intentionally hidden from the current user.
 *
 * Authorization details must not be exposed through the title or description.
 */
export function NotFoundState({
  icon = <NotFoundIcon />,
  ...emptyStateProps
}: NotFoundStateProps) {
  return <EmptyState icon={icon} {...emptyStateProps} />
}

function NotFoundIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-6"
      fill="none"
      viewBox="0 0 24 24"
    >
      <path
        d="M14.5 4H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.5L14.5 4Z"
        stroke="currentColor"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
      <path
        d="M14 4v5h5M9 14h6M12 11v6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.75"
      />
    </svg>
  )
}