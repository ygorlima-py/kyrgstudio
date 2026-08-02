import { Link } from 'react-router'

import type { JobStatusResponse } from '@/shared/api'
import { Badge } from '@/shared/ui/badge'

export interface ActiveJobsProps {
  readonly jobs: readonly JobStatusResponse[]
}

/** Display jobs that are waiting for a worker or currently processing. */
export function ActiveJobs({ jobs }: ActiveJobsProps) {
  if (jobs.length === 0) {
    return null
  }

  return (
    <section aria-labelledby="active-jobs-heading" className="pt-10 sm:pt-12">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h2 className="text-body-lg font-semibold text-text" id="active-jobs-heading">
            In progress
          </h2>
          <p className="mt-1 text-body-sm text-text-muted">
            These projects keep running even when you leave this page.
          </p>
        </div>

        <span className="shrink-0 font-mono text-meta text-text-subtle">
          {jobs.length} {jobs.length === 1 ? 'project' : 'projects'}
        </span>
      </div>

      <div className="mt-5 overflow-hidden rounded-lg border border-border bg-surface">
        {jobs.map((job) => (
          <Link
            className="group grid gap-4 border-b border-border px-5 py-5 transition-colors last:border-b-0 hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-3 focus-visible:ring-inset focus-visible:ring-focus sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:px-6"
            key={job.job_id}
            to={`/app/jobs/${job.job_id}`}
          >
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2.5">
                <h3 className="text-body font-semibold text-text">
                  {getPipelineLabel(job.pipeline_type)}
                </h3>
                <Badge variant={job.status === 'running' ? 'processing' : 'neutral'}>
                  {job.status === 'running' ? 'Processing' : 'Waiting to start'}
                </Badge>
              </div>

              <p className="mt-1 text-body-sm text-text-muted">
                {job.status === 'running'
                  ? 'Your reference is being processed in the background.'
                  : 'Your file is ready and waiting for an available worker.'}
              </p>
            </div>

            <div className="flex items-center justify-between gap-4 sm:justify-end">
              <span className="font-mono text-meta text-text-subtle">
                {formatJobDate(job.created_at)}
              </span>
              <ArrowIcon />
            </div>
          </Link>
        ))}
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
    <svg
      aria-hidden="true"
      className="size-4 shrink-0 text-text-subtle transition-transform group-hover:translate-x-1 group-hover:text-action"
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
