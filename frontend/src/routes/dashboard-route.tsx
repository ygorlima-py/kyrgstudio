import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import { useAuth } from '@/features/auth'
import { ActiveJobs } from '@/features/jobs/components/active-jobs'
import { RecentJobs } from '@/features/jobs/components/recent-jobs'
import {
  isActiveJobStatus,
  isTerminalJobStatus,
} from '@/features/jobs/config/job-status'
import { useUserJobs } from '@/features/jobs/hooks/use-user-jobs'
import { ErrorState } from '@/shared/components/states'
import { Button } from '@/shared/ui/button'
import { Skeleton } from '@/shared/ui/skeleton'

const DASHBOARD_ACTIONS = [
  {
    labelKey: 'dashboard.actions.analysis.label',
    descriptionKey: 'dashboard.actions.analysis.description',
    path: '/app/jobs/new?pipeline=copy_analysis',
  },
  {
    labelKey: 'dashboard.actions.adaptation.label',
    descriptionKey: 'dashboard.actions.adaptation.description',
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

  return (
    <AuthenticatedDashboard
      firstName={getFirstName(session.user.name)}
    />
  )
}

interface AuthenticatedDashboardProps {
  readonly firstName: string | null
}

function AuthenticatedDashboard({
  firstName,
}: AuthenticatedDashboardProps) {
  const { t } = useTranslation()
  const jobsQuery = useUserJobs({ limit: 20, offset: 0 })

  const jobs = jobsQuery.data?.items ?? []
  const activeJobs = jobs.filter((job) =>
    isActiveJobStatus(job.status),
  )
  const recentJobs = jobs.filter((job) =>
    isTerminalJobStatus(job.status),
  )

  const welcomeMessage = firstName
    ? t('dashboard.welcome.withName', { name: firstName })
    : t('dashboard.welcome.default')

  return (
    <div className="mx-auto w-full max-w-6xl">
      <section className="border-b border-border pb-8 sm:pb-10">
        <p className="font-mono text-meta uppercase tracking-[0.14em] text-action">
          {t('dashboard.eyebrow')}
        </p>

        <h1 className="mt-2 font-heading text-heading-3 text-text">
          {welcomeMessage}
        </h1>

      </section>

      <section
        aria-labelledby="dashboard-actions-heading"
        className="pt-8 sm:pt-10"
      >
        <h2
          className="text-body-lg font-semibold text-text"
          id="dashboard-actions-heading"
        >
          {t('dashboard.actions.title')}
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
                <h3 className="text-body-lg font-semibold text-text">
                  {t(action.labelKey)}
                </h3>

                <p className="mt-1 max-w-2xl text-body-sm text-text-muted sm:text-body">
                  {t(action.descriptionKey)}
                </p>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {jobsQuery.isPending ? <JobsLoadingState /> : null}

      {jobsQuery.isError && jobsQuery.data === undefined ? (
        <section className="pt-10 sm:pt-12">
          <ErrorState
            action={
              <Button
                onClick={() => void jobsQuery.refetch()}
                size="sm"
                variant="secondary"
              >
                {t('dashboard.error.retry')}
              </Button>
            }
            description={t('dashboard.error.description')}
            title={t('dashboard.error.title')}
          />
        </section>
      ) : null}

      {jobsQuery.isSuccess && jobs.length === 0 ? (
        <NoJobsState />
      ) : null}

      {jobs.length > 0 ? (
        <>
          <ActiveJobs jobs={activeJobs} />
          <RecentJobs jobs={recentJobs} />

          <div className="mt-7 flex justify-end border-t border-border pt-5">
            <Link
              className="inline-flex items-center gap-2 text-label text-action underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus"
              to="/app/jobs"
            >
              {t('dashboard.history')}
              <ArrowIcon />
            </Link>
          </div>
        </>
      ) : null}
    </div>
  )
}

function JobsLoadingState() {
  const { t } = useTranslation()

  return (
    <section
      aria-label={t('dashboard.loading.label')}
      aria-live="polite"
      className="pt-10 sm:pt-12"
    >
      <span className="sr-only">
        {t('dashboard.loading.description')}
      </span>

      <Skeleton className="h-6 w-36" />

      <div className="mt-5 space-y-3" aria-hidden="true">
        <Skeleton className="h-24 w-full" variant="block" />
        <Skeleton className="h-24 w-full" variant="block" />
      </div>
    </section>
  )
}

function NoJobsState() {
  const { t } = useTranslation()

  return (
    <section
      aria-labelledby="empty-projects-heading"
      className="pt-10 sm:pt-12"
    >
      <div className="border-y border-border py-7 sm:flex sm:items-center sm:justify-between sm:gap-8">
        <div>
          <h2
            className="text-body font-medium text-text"
            id="empty-projects-heading"
          >
            {t('dashboard.empty.title')}
          </h2>

          <p className="mt-1 max-w-2xl text-body-sm text-text-muted">
            {t('dashboard.empty.description')}
          </p>
        </div>

        <Link
          className="mt-4 inline-flex text-label text-action underline-offset-4 hover:underline sm:mt-0 sm:shrink-0"
          to="/app/jobs/new"
        >
          {t('dashboard.empty.action')}
        </Link>
      </div>
    </section>
  )
}

function getFirstName(
  name: string | null | undefined,
): string | null {
  return name?.trim().split(/\s+/)[0] || null
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