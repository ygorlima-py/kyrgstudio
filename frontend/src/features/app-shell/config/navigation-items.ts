export interface AppNavigationItem {
  readonly label: string
  readonly path: string
  readonly exact: boolean
}

/**
 * Navigation destinations shared by desktop and mobile application shells.
 */
export const APP_NAVIGATION_ITEMS: readonly AppNavigationItem[] = [
  {
    label: 'Dashboard',
    path: '/app',
    exact: true,
  },
  {
    label: 'History',
    path: '/app/jobs',
    exact: true,
  },
  {
    label: 'New project',
    path: '/app/jobs/new',
    exact: false,
  },
]
