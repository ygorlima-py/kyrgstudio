import { useTranslation } from 'react-i18next'
import { Link } from 'react-router'

import type { JobStatusResponse } from '@/shared/api'
import { Badge } from '@/shared/ui/badge'

export interface RecentJobsProps {
  readonly jobs: readonly JobStatusResponse[]
}

/** Display completed and failed jobs with a status-aware destination. */
export function RecentJobs({ jobs }: RecentJobsProps) {
  const { i18n, t } = useTranslation()

  if (jobs.length === 0) {
    return null
  }

  const locale = i18n.resolvedLanguage?.startsWith('en')
    ? 'en-US'
    : 'pt-BR'

  return (
    <section
      aria-labelledby="recent-jobs-heading"
      className="pt-10 sm:pt-12"
    >
      <div>
        <h2
          className="text-body-lg font-semibold text-text"
          id="recent-jobs-heading"
        >
          {t('jobs.recent.title')}
        </h2>

        <p className="mt-1 text-body-sm text-text-muted">
          {t('jobs.recent.description')}
        </p>
      </div>

      <div className="mt-5 divide-y divide-border border-y border-border">
        {jobs.map((job) => {
          const completed = job.status === 'completed'

          const pipelineLabel =
            job.pipeline_type === 'copy_adaptation'
              ? t('jobs.pipeline.adaptation')
              : t('jobs.pipeline.analysis')

          return (
            <Link
              className="group grid gap-3 py-5 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-6"
              key={job.job_id}
              to={
                completed
                  ? `/app/jobs/${job.job_id}/result`
                  : `/app/jobs/${job.job_id}`
              }
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h3 className="text-body font-semibold text-text group-hover:text-action">
                    {pipelineLabel}
                  </h3>

                  <Badge
                    variant={completed ? 'success' : 'danger'}
                  >
                    {completed
                      ? t('jobs.recent.status.completed')
                      : t('jobs.recent.status.failed')}
                  </Badge>
                </div>

                <p className="mt-1 font-mono text-meta text-text-subtle">
                  {t('jobs.projectNumber', {
                    id: job.job_id,
                  })}{' '}
                  ·{' '}
                  {formatJobDate(
                    job.finished_at ?? job.created_at,
                    locale,
                    t('jobs.dateUnavailable'),
                  )}
                </p>
              </div>

              <span className="inline-flex items-center gap-2 text-label text-action">
                {completed
                  ? t('jobs.recent.viewResult')
                  : t('jobs.recent.viewDetails')}

                <ArrowIcon />
              </span>
            </Link>
          )
        })}
      </div>
    </section>
  )
}

function formatJobDate(
  value: string,
  locale: string,
  unavailableLabel: string,
): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return unavailableLabel
  }

  return new Intl.DateTimeFormat(locale, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function ArrowIcon() {
  return (
    <svg
      aria-hidden="true"
      className="size-4 shrink-0"
      fill="none"
      viewBox="0 0 16 16"
    >
      <path
        d="M3 8h10m-4-4 4 4-4 4"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="1.5"
      />
    </svg>
  )
}