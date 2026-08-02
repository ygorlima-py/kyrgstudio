import { Link } from 'react-router'

import type { JobStatusResponse } from '@/shared/api'
import { Badge } from '@/shared/ui/badge'

export interface RecentJobsProps {
  readonly jobs: readonly JobStatusResponse[]
}

/** Display completed and failed jobs with a status-aware destination. */
export function RecentJobs({ jobs }: RecentJobsProps) {
  if (jobs.length === 0) {
    return null
  }

  return (
    <section aria-labelledby="recent-jobs-heading" className="pt-10 sm:pt-12">
      <div>
        <h2 className="text-body-lg font-semibold text-text" id="recent-jobs-heading">
          Recent projects
        </h2>
        <p className="mt-1 text-body-sm text-text-muted">
          Return to a finished result or review a project that could not be completed.
        </p>
      </div>

      <div className="mt-5 divide-y divide-border border-y border-border">
        {jobs.map((job) => {
          const completed = job.status === 'completed'

          return (
            <Link
              className="group grid gap-3 py-5 focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-focus sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-6"
              key={job.job_id}
              to={completed ? `/app/jobs/${job.job_id}/result` : `/app/jobs/${job.job_id}`}
            >
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2.5">
                  <h3 className="text-body font-semibold text-text group-hover:text-action">
                    {getPipelineLabel(job.pipeline_type)}
                  </h3>
                  <Badge variant={completed ? 'success' : 'danger'}>
                    {completed ? 'Completed' : 'Failed'}
                  </Badge>
                </div>

                <p className="mt-1 font-mono text-meta text-text-subtle">
                  Project #{job.job_id} · {formatJobDate(job.finished_at ?? job.created_at)}
                </p>
              </div>

              <span className="inline-flex items-center gap-2 text-label text-action">
                {completed ? 'View result' : 'View details'}
                <ArrowIcon />
              </span>
            </Link>
          )
        })}
      </div>
    </section>
  )
}

function getPipelineLabel(pipelineType: JobStatusResponse['pipeline_type']): string {
  return pipelineType === 'copy_adaptation' ? 'Copy adaptation' : 'Copy analysis'
}

function formatJobDate(value: string): string {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return 'Date unavailable'
  }

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

function ArrowIcon() {
  return (
    <svg aria-hidden="true" className="size-4 shrink-0" fill="none" viewBox="0 0 16 16">
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
