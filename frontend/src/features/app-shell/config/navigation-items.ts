export interface AppNavigationItem {
  readonly labelKey:
    | 'appNavigation.dashboard'
    | 'appNavigation.history'
    | 'appNavigation.newProject'
  readonly path: string
  readonly exact: boolean
}

/**
 * Navigation destinations shared by desktop and mobile application shells.
 */
export const APP_NAVIGATION_ITEMS: readonly AppNavigationItem[] = [
  {
    labelKey: 'appNavigation.dashboard',
    path: '/app',
    exact: true,
  },
  {
    labelKey: 'appNavigation.history',
    path: '/app/jobs',
    exact: true,
  },
  {
    labelKey: 'appNavigation.newProject',
    path: '/app/jobs/new',
    exact: false,
  },
]