import { Link } from 'react-router'

import { useAuth } from '@/features/auth'

const DASHBOARD_ACTIONS = [
  {
    label: 'Analyze a copy',
    description:
      'Reveal the hook, argument, offer, proof, objections, and structure behind a sales message.',
    path: '/app/jobs/new?pipeline=copy_analysis',
  },
  {
    label: 'Adapt a copy',
    description:
      'Use the strategy of an existing message to create a new script for your own offer.',
    path: '/app/jobs/new?pipeline=copy_adaptation',
  },
] as const

/**
 * Initial authenticated page with the main product actions and project history.
 */
export function DashboardRoute() {
  const session = useAuth()

  if (session.status !== 'authenticated') {
    return null
  }

  const firstName = session.user.name?.trim().split(/\s+/)[0]

  return (
    <div className="mx-auto w-full max-w-6xl">
      <section className="border-b border-border pb-8 sm:pb-10">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          Workspace
        </p>

        <h1 className="mt-2 font-heading text-heading-3 text-text">
          {firstName ? `Welcome back, ${firstName}` : 'Welcome back'}
        </h1>

        <p className="mt-2 max-w-2xl text-body text-text-muted">
          Choose what you want to do with your next sales reference.
        </p>
      </section>

      <section aria-labelledby="dashboard-actions-heading" className="pt-8 sm:pt-10">
        <h2
          className="text-body-lg font-semibold text-text"
          id="dashboard-actions-heading"
        >
          Start a new project
        </h2>

        <div className="mt-5 grid gap-4 md:grid-cols-2">
          {DASHBOARD_ACTIONS.map((action, index) => (
            <Link
              className="group flex min-h-44 flex-col justify-between rounded-lg border border-border bg-surface p-5 transition-[border-color,box-shadow] hover:border-border-strong hover:shadow-sm focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus sm:p-6"
              key={action.path}
              to={action.path}
            >
              <div className="flex items-center justify-between gap-4">
                <span className="font-mono text-meta text-text-subtle">
                  {String(index + 1).padStart(2, '0')}
                </span>

                <ArrowIcon />
              </div>

              <div className="mt-8">
                <h3 className="text-body-lg font-semibold text-text">{action.label}</h3>

                <p className="mt-1 max-w-2xl text-body-sm text-text-muted sm:text-body">
                  {action.description}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section aria-labelledby="recent-projects-heading" className="pt-10 sm:pt-12">
        <div>
          <h2
            className="text-body-lg font-semibold text-text"
            id="recent-projects-heading"
          >
            Recent projects
          </h2>

          <p className="mt-2 text-body text-text-muted">
            Your latest analyses and adaptations will be available here.
          </p>
        </div>

        <div className="mt-5 border-y border-border py-7 sm:flex sm:items-center sm:justify-between sm:gap-8">
          <div>
            <p className="text-body font-medium text-text">No projects yet</p>
            <p className="mt-1 max-w-2xl text-body-sm text-text-muted">
              Your completed analyses and adaptations will appear here.
            </p>
          </div>

          <Link
            className="mt-4 inline-flex text-label text-action underline-offset-4 hover:underline sm:mt-0 sm:shrink-0"
            to="/app/jobs/new"
          >
            Start your first project
          </Link>
        </div>
      </section>
    </div>
  )
}

function ArrowIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-5 shrink-0 text-text-subtle transition-transform group-hover:translate-x-1 group-hover:text-action"
      fill="none"
      viewBox="0 0 20 20"
    >
      <path
        d="M4 10h12m-5-5 5 5-5 5"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  )
}
